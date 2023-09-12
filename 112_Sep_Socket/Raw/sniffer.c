#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/ip.h>

void process_packet(unsigned char *buffer, int size) {
    struct ip *ip_hdr = (struct ip *)buffer;

    printf("Source IP: %s\n", inet_ntoa(ip_hdr->ip_src));
    printf("Destination IP: %s\n", inet_ntoa(ip_hdr->ip_dst));
    printf("Protocol: %d\n", ip_hdr->ip_p);
    printf("Packet Size: %d bytes\n", ntohs(ip_hdr->ip_len));
    printf("\n");
}

int main() {
    int sockfd;
    unsigned char buffer[65536];

    // Create a raw socket
    sockfd = socket(AF_INET, SOCK_RAW, IPPROTO_TCP); // Capture TCP packets (you can change this)
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    while (1) {
        int packet_size = recvfrom(sockfd, buffer, sizeof(buffer), 0, NULL, NULL);
        if (packet_size < 0) {
            perror("Packet capture error");
            exit(1);
        }

        process_packet(buffer, packet_size);
    }

    close(sockfd);

    return 0;
}
