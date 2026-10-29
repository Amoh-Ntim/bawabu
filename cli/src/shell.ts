/**
 * A small shell lexer: enough of POSIX sh to see what a command line would run.
 * Returns null for input it can't read safely (unbalanced quotes, unterminated heredocs).
 */

export interface Command {
  words: string[];
  /** Heredoc and here-string bodies fed to this command's stdin. */
  stdin: string[];
  /** Files redirected into stdin (`< file`). */
  inputs: string[];
  /** Files written by redirection (`> file`, `>> file`). */
  writes: string[];
}

export interface Lexed {
  commands: Command[];
  /** Contents of $(...) and backticks: they run too, so callers analyze them separately. */
  substitutions: string[];
}

/** Stands in for a command substitution inside a word, so the word can't pass as a package name. */
export const SUBSTITUTION = "$(…)";

const OPERATORS = ["&&", "||", ";;", "|&", ";", "|", "&", "\n", "(", ")"];
const REDIRECT = /^(&>>|&>|<<<|<<-|<<|>>|>\||>&|<&|<>|>|<)/;

const newCommand = (): Command => ({ words: [], stdin: [], inputs: [], writes: [] });

export const shellQuote = (s: string) => `'${s.replace(/'/g, `'\\''`)}'`;

export function lex(input: string): Lexed | null {
  const commands: Command[] = [];
  const substitutions: string[] = [];
  const heredocs: Array<{ delimiter: string; stripTabs: boolean; expand: boolean; command: Command; slot: number }> = [];
  let current = newCommand();
  let word = "";
  let inWord = false;
  let quoted = false;
  let redirect: string | null = null;
  let i = 0;

  const endWord = () => {
    if (!inWord) return;
    if (redirect === null) current.words.push(word);
    else if (redirect === "<<" || redirect === "<<-") {
      heredocs.push({ delimiter: word, stripTabs: redirect === "<<-", expand: !quoted, command: current, slot: current.stdin.length });
      current.stdin.push("");
    } else if (redirect === "<<<") current.stdin.push(word);
    else if (redirect === "<") current.inputs.push(word);
    else if (redirect !== ">&" && redirect !== "<&") current.writes.push(word); // >& and <& duplicate fds (2>&1)
    redirect = null;
    word = "";
    inWord = false;
    quoted = false;
  };
  const endCommand = () => {
    endWord();
    if (current.words.length || current.stdin.length || current.inputs.length || current.writes.length) commands.push(current);
    current = newCommand();
  };
  // Heredoc bodies start on the line after the operator. Returns the index after the last body, or -1.
  const readHeredocBodies = (from: number): number => {
    let j = from;
    for (const h of heredocs) {
      const lines: string[] = [];
      for (;;) {
        if (j >= input.length) return -1;
        const newline = input.indexOf("\n", j);
        const end = newline < 0 ? input.length : newline;
        const line = h.stripTabs ? input.slice(j, end).replace(/^\t+/, "") : input.slice(j, end);
        j = end + 1;
        if (line === h.delimiter) break;
        lines.push(line);
      }
      const body = lines.join("\n");
      h.command.stdin[h.slot] = body;
      // An unquoted delimiter means $(...) in the body runs.
      if (h.expand && !collectSubstitutions(body, substitutions)) return -1;
    }
    heredocs.length = 0;
    return j;
  };

  while (i < input.length) {
    const c = input[i];

    if (c === "'") {
      const end = input.indexOf("'", i + 1);
      if (end < 0) return null;
      word += input.slice(i + 1, end);
      inWord = quoted = true;
      i = end + 1;
      continue;
    }
    if (c === '"') {
      inWord = quoted = true;
      i++;
      while (i < input.length && input[i] !== '"') {
        const d = input[i];
        if (d === "\\" && '$`"\\\n'.includes(input[i + 1] ?? "")) {
          word += input[i + 1];
          i += 2;
        } else if ((d === "$" && input[i + 1] === "(") || d === "`") {
          i = d === "`" ? readBackticks(input, i, substitutions) : readParens(input, i, substitutions);
          if (i < 0) return null;
          word += SUBSTITUTION;
        } else {
          word += d;
          i++;
        }
      }
      if (i >= input.length) return null;
      i++;
      continue;
    }
    if (c === "\\") {
      if (i + 1 < input.length && input[i + 1] !== "\n") {
        word += input[i + 1];
        inWord = quoted = true;
      }
      i += 2;
      continue;
    }
    if ((c === "$" && input[i + 1] === "(") || c === "`") {
      i = c === "`" ? readBackticks(input, i, substitutions) : readParens(input, i, substitutions);
      if (i < 0) return null;
      word += SUBSTITUTION;
      inWord = true;
      continue;
    }
    if (c === "#" && !inWord) {
      while (i < input.length && input[i] !== "\n") i++;
      continue;
    }
    if (c === " " || c === "\t" || c === "\r") {
      endWord();
      i++;
      continue;
    }
    if (c === ">" || c === "<" || (c === "&" && input[i + 1] === ">")) {
      // A bare fd number before the operator (the 2 in 2>&1) isn't a word.
      if (inWord && !quoted && /^\d+$/.test(word)) {
        word = "";
        inWord = false;
      } else endWord();
      const op = input.slice(i).match(REDIRECT)![0];
      i += op.length;
      redirect = op;
      continue;
    }
    const op = OPERATORS.find((o) => input.startsWith(o, i));
    if (op) {
      endCommand();
      i += op.length;
      if (op === "\n" && heredocs.length) {
        i = readHeredocBodies(i);
        if (i < 0) return null;
      }
      continue;
    }
    word += c;
    inWord = true;
    i++;
  }
  endCommand();
  return heredocs.length ? null : { commands, substitutions };
}

// Both readers take the index of "$(" or "`" and return the index just past the end, or -1 if it never closes.
function readParens(text: string, start: number, out: string[]): number {
  let depth = 0;
  for (let j = start + 1; j < text.length; j++) {
    const c = text[j];
    if (c === "\\") j++;
    else if (c === "'") {
      j = text.indexOf("'", j + 1);
      if (j < 0) return -1;
    } else if (c === "(") depth++;
    else if (c === ")" && --depth === 0) {
      out.push(text.slice(start + 2, j));
      return j + 1;
    }
  }
  return -1;
}

function readBackticks(text: string, start: number, out: string[]): number {
  for (let j = start + 1; j < text.length; j++) {
    if (text[j] === "\\") j++;
    else if (text[j] === "`") {
      out.push(text.slice(start + 1, j));
      return j + 1;
    }
  }
  return -1;
}

function collectSubstitutions(text: string, out: string[]): boolean {
  for (let j = 0; j < text.length; j++) {
    if (text[j] === "\\") j++;
    else if ((text[j] === "$" && text[j + 1] === "(") || text[j] === "`") {
      const end = text[j] === "`" ? readBackticks(text, j, out) : readParens(text, j, out);
      if (end < 0) return false;
      j = end - 1;
    }
  }
  return true;
}
