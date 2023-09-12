#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define SERVER_IP "127.0.0.1" // The IP address of the server
#define PORT 12345            // The port number of the server

int main() {
    int sockfd;
    struct sockaddr_in server_addr;
    char message[] = "Hello, server!";
    char buffer[1024];

    // Create a UDP socket
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Initialize server address
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);
    server_addr.sin_port = htons(PORT);

    // Send a message to the server
    sendto(sockfd, message, strlen(message), 0, (struct sockaddr *)&server_addr, sizeof(server_addr));

    // Receive a response from the server
    int bytes_received = recvfrom(sockfd, buffer, sizeof(buffer), 0, NULL, NULL);
    if (bytes_received < 0) {
        perror("Error receiving data");
        exit(1);
    }

    // Null-terminate the received data
    buffer[bytes_received] = '\0';

    printf("Received from server: %s\n", buffer);

    close(sockfd);

    return 0;
}
