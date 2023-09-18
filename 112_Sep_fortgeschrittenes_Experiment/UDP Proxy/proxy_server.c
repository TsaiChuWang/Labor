#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define BUFFER_SIZE 1024
#define TARGET_IP "127.0.0.1"  // Replace with the target server IP
#define TARGET_PORT 1996      // Replace with the target server port
#define FILTEREDWORD "eeff"
#define REPLACEDWORD "eeff"

void process_packet(int proxy_socket);

char* payload_handle(char* origin_payload,int size_origin_payload);

int main() {
    int proxy_socket;
    struct sockaddr_in proxy_addr;

    // Create a socket
    proxy_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (proxy_socket == -1) {
        perror("Socket creation is failed");
        exit(EXIT_FAILURE);
    }

    // Initialize proxy address structure
    memset(&proxy_addr, '\0', sizeof(proxy_addr));
    proxy_addr.sin_family = AF_INET;
    proxy_addr.sin_port = htons(2000);
    proxy_addr.sin_addr.s_addr = INADDR_ANY;

    // Bind the socket to the proxy address
    int bind_status = bind(proxy_socket, (struct sockaddr *)&proxy_addr, sizeof(proxy_addr));
    if (bind_status < 0) {
        perror("Binding failed");
        exit(EXIT_FAILURE);
    }

    printf("Proxy server is running. Listening for incoming packets...\n");

    while (1) {
        process_packet(proxy_socket);
    }

    close(proxy_socket);
    return 0;
}

void process_packet(int proxy_socket) {
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    char buffer[BUFFER_SIZE];

    // Receive packet from client
    int recv_size = recvfrom(proxy_socket, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&client_addr, &addr_len);

    if (recv_size < 0) {
        perror("Packet receive failed");
        return;
    }

    // Null-terminate the received data
    *(buffer+recv_size) = '\0';

    char* s =payload_handle(buffer,recv_size);

    // Filter keywords (e.g., "filterme")
    // if (strstr(buffer, "filterme") != NULL) {
    //     printf("Filtered keyword detected: %s\n", buffer);
    // } else {
    //     printf("Forwarding packet to target server: %s\n", buffer);

    //     // Forward valid packets to target server
    //     struct sockaddr_in target_addr;
    //     target_addr.sin_family = AF_INET;
    //     target_addr.sin_port = htons(TARGET_PORT);
    //     target_addr.sin_addr.s_addr = inet_addr(TARGET_IP);

    //     sendto(proxy_socket, buffer, recv_size, 0, (struct sockaddr *)&target_addr, sizeof(target_addr));
    // }
}

char* payload_handle(char* origin_payload,int size_origin_payload){
    char* handled_payload = (char*)malloc(sizeof(char)*size_origin_payload);
    memset(handled_payload, '\0', sizeof(handled_payload));
    printf("%s + %s\n",origin_payload,FILTEREDWORD);

    return handled_payload;
}