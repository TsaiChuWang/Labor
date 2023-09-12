#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/tcp.h>

#define TARGET_IP "127.0.0.1"
#define START_PORT 1
#define END_PORT 1024

int main() {
    int sockfd;
    struct sockaddr_in target_addr;
    struct tcphdr tcp_hdr;
    
    // Create a raw socket
    sockfd = socket(AF_INET, SOCK_RAW, IPPROTO_TCP);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Initialize target address
    memset(&target_addr, 0, sizeof(target_addr));
    target_addr.sin_family = AF_INET;
    target_addr.sin_addr.s_addr = inet_addr(TARGET_IP);

    // Loop through ports and scan
    for (int port = START_PORT; port <= END_PORT; port++) {
        // Initialize TCP header
        memset(&tcp_hdr, 0, sizeof(tcp_hdr));
        tcp_hdr.source = htons(12345);  // Your source port
        tcp_hdr.dest = htons(port);
        tcp_hdr.seq = 0;
        tcp_hdr.ack_seq = 0;
        tcp_hdr.doff = 5;  // Data offset
        tcp_hdr.syn = 1;   // SYN flag for TCP scan
        tcp_hdr.window = htons(5840); // Maximum allowed window size
        tcp_hdr.check = 0; // Checksum will be filled later
        tcp_hdr.urg_ptr = 0;
        
        // Send the TCP packet
        sendto(sockfd, &tcp_hdr, sizeof(tcp_hdr), 0, (struct sockaddr *)&target_addr, sizeof(target_addr));
        
        // Wait for a response (you'll need to implement a timeout mechanism)
        
        // Check the response to determine if the port is open
        // You need to handle ICMP responses, TCP SYN-ACK, etc.
        
        // Print the result
    }

    close(sockfd);

    return 0;
}
