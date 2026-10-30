/* Bawabu sandbox resolver shim (LD_PRELOAD'd into the package's processes).
 *
 * Modal manages /etc/resolv.conf, so we can't repoint DNS the normal way. Instead we override
 * getaddrinfo so that every hostname resolves to loopback (127.0.0.1 / ::1), where our fake-internet
 * sink is listening. Two effects:
 *   - the package's outbound HTTP(S) connects to the sink, so we capture what it tried to send;
 *   - we append every resolved name to BAWABU_RESOLVE_LOG, so we record the *intended* destination
 *     even if the request never completes.
 * Numeric IPs are passed through to the real resolver so localhost/explicit-IP traffic is unchanged.
 *
 * Build: gcc -shared -fPIC -o dnsshim.so dnsshim.c -ldl
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dlfcn.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void log_name(const char *node) {
    const char *path = getenv("BAWABU_RESOLVE_LOG");
    if (!path || !node) return;
    FILE *f = fopen(path, "a");
    if (f) { fprintf(f, "%s\n", node); fclose(f); }
}

int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res) {
    /* Pass numeric hosts (incl. AI_NUMERICHOST) straight through to the real resolver. */
    if (node) {
        struct in_addr a4; struct in6_addr a6;
        int numeric = inet_pton(AF_INET, node, &a4) == 1 || inet_pton(AF_INET6, node, &a6) == 1;
        if (!numeric) {
            log_name(node);
            int want6 = hints && hints->ai_family == AF_INET6;
            struct addrinfo *ai = calloc(1, sizeof(*ai));
            if (want6) {
                struct sockaddr_in6 *sa = calloc(1, sizeof(*sa));
                sa->sin6_family = AF_INET6;
                sa->sin6_addr = in6addr_loopback;
                sa->sin6_port = service ? htons((unsigned short)atoi(service)) : 0;
                ai->ai_family = AF_INET6; ai->ai_addrlen = sizeof(*sa);
                ai->ai_addr = (struct sockaddr *)sa;
            } else {
                struct sockaddr_in *sa = calloc(1, sizeof(*sa));
                sa->sin_family = AF_INET;
                sa->sin_addr.s_addr = htonl(INADDR_LOOPBACK);
                sa->sin_port = service ? htons((unsigned short)atoi(service)) : 0;
                ai->ai_family = AF_INET; ai->ai_addrlen = sizeof(*sa);
                ai->ai_addr = (struct sockaddr *)sa;
            }
            ai->ai_socktype = hints && hints->ai_socktype ? hints->ai_socktype : SOCK_STREAM;
            ai->ai_protocol = hints ? hints->ai_protocol : 0;
            ai->ai_canonname = strdup(node);
            ai->ai_next = NULL;
            *res = ai;
            return 0;
        }
    }
    int (*real)(const char *, const char *, const struct addrinfo *, struct addrinfo **) =
        dlsym(RTLD_NEXT, "getaddrinfo");
    return real(node, service, hints, res);
}
