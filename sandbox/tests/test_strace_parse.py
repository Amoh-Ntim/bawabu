from bawabu_sandbox import strace_parse


def test_openat_reads_and_writes():
    text = (
        '1234 openat(AT_FDCWD, "/root/.npmrc", O_RDONLY|O_CLOEXEC) = 3\n'
        '1234 openat(AT_FDCWD, "/work/out.log", O_WRONLY|O_CREAT) = 4\n'
    )
    facts = strace_parse.parse(text)
    assert ("/root/.npmrc", "O_RDONLY|O_CLOEXEC") in facts.opened
    assert facts.read_opens() == ["/root/.npmrc"]


def test_execve_argv():
    text = '1200 execve("/bin/sh", ["sh", "-c", "cat /root/.npmrc"], 0x7ff /* 20 vars */) = 0\n'
    facts = strace_parse.parse(text)
    assert facts.execs == [["/bin/sh", "-c", "cat /root/.npmrc"]]


def test_connect_ipv4_with_port():
    text = '999 connect(5, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
    facts = strace_parse.parse(text)
    assert facts.connects == [("127.0.0.1", 443)]


def test_unix_socket_ignored():
    text = '10 connect(3, {sa_family=AF_UNIX, sun_path="/var/run/nscd/socket"}, 110) = -1\n'
    assert strace_parse.parse(text).connects == []


def test_unfinished_resumed_stitched():
    text = (
        '500 openat(AT_FDCWD, "/root/.ssh/id_rsa" <unfinished ...>\n'
        '501 execve("/usr/bin/curl", ["curl", "x"], 0x0) = 0\n'
        '500 <... openat resumed>, O_RDONLY) = 6\n'
    )
    facts = strace_parse.parse(text)
    assert ("/root/.ssh/id_rsa", "O_RDONLY") in facts.opened
    assert ["/usr/bin/curl", "x"] in facts.execs
