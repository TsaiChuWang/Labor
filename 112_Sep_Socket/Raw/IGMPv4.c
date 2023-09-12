#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <netinet/ip.h>
#include <netinet/igmp.h>

#define MULTICAST_GROUP "239.0.0.1"  // Replace with your desired multicast group
#define INTERFACE "eth0"  // Replace with your network interface name

int main() {
    int sockfd;
    struct sockaddr_in dest_addr;
    struct ip *ip_hdr;
    struct igmp igmp_hdr;

    // Create a raw socket
    sockfd = socket(AF_INET, SOCK_RAW, IPPROTO_IGMP);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Set the destination address
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_addr.s_addr = inet_addr(MULTICAST_GROUP);

    // Set the outgoing interface (you may need to use system-specific methods to set the interface)
    setsockopt(sockfd, IPPROTO_IP, IP_MULTICAST_IF, INTERFACE, strlen(INTERFACE));

    // Create the IGMP packet
    memset(&igmp_hdr, 0, sizeof(igmp_hdr));
    igmp_hdr.igmp_type = IGMP_HOST_MEMBERSHIP_REPORT;  // Join the multicast group
    igmp_hdr.igmp_group.s_addr = inet_addr(MULTICAST_GROUP);

    // Create the IP packet
    memset(&ip_hdr, 0, sizeof(ip_hdr));
    ip_hdr->ip_src.s_addr = INADDR_ANY;  // Source address (0.0.0.0)
    ip_hdr->ip_dst.s_addr = inet_addr(MULTICAST_GROUP);  // Destination address
    ip_hdr->ip_p = IPPROTO_IGMP;  // Protocol type: IGMP
    ip_hdr->ip_len = sizeof(struct ip) + sizeof(struct igmp);
    ip_hdr->ip_ttl = 1;  // Time-to-live

    // Send the IGMP packet
    sendto(sockfd, &igmp_hdr, sizeof(igmp_hdr), 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));

    close(sockfd);

    return 0;
}
