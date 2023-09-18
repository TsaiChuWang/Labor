#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define SERVER_IP "127.0.0.1"  
#define SERVER_PORT 2000      
#define BUFFER_SIZE 1024

/* Constatn for EXIT*/
#define EXITWORD "exit"
#define SIZE_EXITWORD 4

/* Status code*/
#define TRUE 1
#define FALSE 0
#define FAILURE -1

int checkIfItExit(char* origin_payload,int size_origin_payload);

int main() {
    int client_socket;
    struct sockaddr_in server_addr;

    
    client_socket = socket(AF_INET, SOCK_DGRAM, 0); // Create a UDP socket
    if (client_socket == FAILURE) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }
    memset(&server_addr, '\0', sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);

    while(TRUE){
        char buffer[BUFFER_SIZE];

        printf("client : ");
        fgets(buffer, BUFFER_SIZE, stdin);  // get the input message

        sendto(client_socket, buffer, strlen(buffer), 0, (struct sockaddr *)&server_addr, sizeof(server_addr)); //send packet

        int code =checkIfItExit(buffer,strlen(buffer));
        if(code == TRUE)    exit(0);
    }

    // Close the client socket when done
    close(client_socket);
    return 0;
}

int checkIfItExit(char* origin_payload,int size_origin_payload){
    if(size_origin_payload > SIZE_EXITWORD+1)   // length > 4
        return ;
    
    int check = TRUE;
    for(int index=0;index <SIZE_EXITWORD ;index++){ // check string is exit
        check = check & (*(origin_payload+index) == *(EXITWORD+index));
        if(check == FALSE) break;
    }
    return check;
}