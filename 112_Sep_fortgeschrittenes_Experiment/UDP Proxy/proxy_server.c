#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define BUFFER_SIZE 1024
#define TARGET_IP "127.0.0.1"  // Replace with the target server IP
#define TARGET_PORT 1996      // Replace with the target server port
#define FILTEREDWORD "eeff"
#define SIZE_FILTEREDWORD 4
#define REPLACEDWORD "aabb"
#define SIZE_REPLACEDWORD 4
#define CHANGEWORD "ccdd"
#define TRUE 1
#define FALSE 0
#define ERROR -1

#define FILTER 1

void process_packet(int proxy_socket);

char* payload_handle(char* origin_payload,int size_origin_payload,int* code);
int checkIfitKeyword(char* origin_payload,int size_origin_payload);
void checkfilterAndChange(char* origin_payload,int size_origin_payload,int* code);

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

    while (TRUE) {
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
    *(buffer+recv_size-1) = '\0';

    int code = 0;
    char* s =payload_handle(buffer,recv_size,&code);
    printf("code = %d for %10s\n",code,s);

    if(code == FILTER)
        continue;
}

char* payload_handle(char* origin_payload, int size_origin_payload, int* code){
    char* handled_payload = (char*)malloc(sizeof(char)*size_origin_payload);
    memset(handled_payload, '\0', sizeof(handled_payload));

    if(size_origin_payload < sizeof(FILTEREDWORD) && size_origin_payload <sizeof(REPLACEDWORD))
        return origin_payload;

    if(checkIfitKeyword(origin_payload,size_origin_payload) == TRUE){
        *code = 1;
        return "";
    }else{
        checkfilterAndChange(origin_payload,size_origin_payload,code);

        
    }
        
    printf("%s + %s + %d \n",origin_payload,FILTEREDWORD,checkIfitKeyword(origin_payload,size_origin_payload));

    return origin_payload;
}

int checkIfitKeyword(char* origin_payload,int size_origin_payload){
    char first = *FILTEREDWORD;
    char* substring = (char*)malloc(sizeof(char)*sizeof(FILTEREDWORD));
    memset(substring, '\0', sizeof(substring));
    int check = FALSE;

    for(int index =0;index<size_origin_payload;index++){
        if(*(origin_payload + index) == first)
        {
            if(index > size_origin_payload - SIZE_FILTEREDWORD - 1)
                return FALSE;

            check = TRUE;
            for(int j = 0; j < SIZE_FILTEREDWORD; j++){
                check = (*(origin_payload+index+j) == *(FILTEREDWORD + j));
                // printf("index= %d original = %c filter = %c check = %d\n",index+j,*(origin_payload+index+j),*(FILTEREDWORD + j),check);
                if(check == 0) break;
            }
            if(check)
                return TRUE;
        }
    }
    return FALSE;
}

void checkfilterAndChange(char* origin_payload,int size_origin_payload,int* code){
    char first = *REPLACEDWORD;
    char* substring = (char*)malloc(sizeof(char)*(REPLACEDWORD+1));
    memset(substring, '\0', sizeof(substring));

    int check = FALSE;

    for(int index =0;index<size_origin_payload;index++){
        if(*(origin_payload + index) == first)
        {
            if(index > size_origin_payload - REPLACEDWORD - 1)
                return;

            check = TRUE;
            for(int j = 0; j < SIZE_REPLACEDWORD; j++){
                check = (*(origin_payload+index+j) == *(REPLACEDWORD + j));
                // printf("index= %d original = %c filter = %c check = %d\n",index+j,*(origin_payload+index+j),*(FILTEREDWORD + j),check);
                if(check == 0) break;
            }
            if(check){
                *code = 2;
                for(int j = 0; j < SIZE_REPLACEDWORD; j++)
                    *(origin_payload+index+j) = *(CHANGEWORD+j);
            }
        }
    }
}