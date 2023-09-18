#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/if_ether.h>
#include <arpa/inet.h>

#define BUFFER_SIZE 1024
#define TARGET_IP "127.0.0.1" 
#define TARGET_PORT 1996     

/* FILTER : word that do not appear */
#define FILTEREDWORD "eeff"
#define SIZE_FILTEREDWORD 4

/* REPLACED : word that be replaced to another word */
#define REPLACEDWORD "aabb"
#define SIZE_REPLACEDWORD 4
#define CHANGEWORD "ccdd"

/* EXIT : Word that tells close the process*/
#define EXITWORD "exit"
#define SIZE_EXITWORD 4

/* Status code */
#define TRUE 1
#define FALSE 0
#define ERROR -1

/* Code that indicate how to handle the payload*/
#define FILTER 1
#define REPLACE 2
#define NOTHING 0
#define EXIT -1

void process_packet(int proxy_socket,int* code);

/* payload handle */
char* payload_handle(char* origin_payload,int size_origin_payload,int* code);
int checkIfitKeyword(char* origin_payload,int size_origin_payload);
void checkfilterAndChange(char* origin_payload,int size_origin_payload,int* code);
void checkIfItExit(char* origin_payload,int size_origin_payload,int* code);

int main() {
    int proxy_socket;
    struct sockaddr_in proxy_addr;

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
        int code =0;
        process_packet(proxy_socket,&code);

        if(code == EXIT)
            exit(0);
    }

    close(proxy_socket);
    return 0;
}

void process_packet(int proxy_socket,int* code) {
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    char buffer[BUFFER_SIZE];

    int recv_size = recvfrom(proxy_socket, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&client_addr, &addr_len);
    
    struct ether_header* eth_header = (struct ether_header*)buffer;
    struct iphdr* ipheader_pointer;

    struct in_addr source_ip_address;
    source_ip_address.s_addr = ipheader_pointer->saddr;

    // Convert the binary IP to a human-readable string
    char source_ip_address_string[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &(source_ip_address), source_ip_address_string, INET_ADDRSTRLEN);

    if (recv_size < 0) {
        perror("Packet receive failed");
        return;
    }

    *(buffer+recv_size-1) = '\0';

    char* string = payload_handle(buffer, recv_size, code);

    if(*code == FILTER)
        return;
    if(*code == REPLACE)
        printf("[%15s] : %s \n", source_ip_address_string, string);
    if(*code == NOTHING)
        printf("[%15s] : %s \n" ,source_ip_address_string, string);
    if(*code == EXIT)
        printf("\x1B[0;31m""[%15s] : %s \n",source_ip_address_string,string);
}

char* payload_handle(char* origin_payload, int size_origin_payload, int* code){
    char* handled_payload = (char*)malloc(sizeof(char)*size_origin_payload);
    memset(handled_payload, '\0', sizeof(handled_payload));

    if(size_origin_payload < sizeof(FILTEREDWORD) && size_origin_payload <sizeof(REPLACEDWORD))
        return origin_payload;

    *code = checkIfitKeyword(origin_payload,size_origin_payload);
    if(*code == FILTER)
        return "";

    checkfilterAndChange(origin_payload,size_origin_payload,code);
    if(*code == REPLACE)
        return origin_payload;

    checkIfItExit(origin_payload,size_origin_payload,code);
    if(*code == EXIT)
        return "EXIT";

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
    char* substring = (char*)malloc(sizeof(char)*(SIZE_REPLACEDWORD+1));
    memset(substring, '\0', sizeof(substring));

    int check = FALSE;

    for(int index =0;index<size_origin_payload;index++){
        if(*(origin_payload + index) == first)
        {
            if(index > size_origin_payload - SIZE_REPLACEDWORD - 1)
                return;

            check = TRUE;
            for(int j = 0; j < SIZE_REPLACEDWORD; j++){
                check = (*(origin_payload+index+j) == *(REPLACEDWORD + j));
                if(check == 0) break;
            }
            if(check){
                *code = REPLACE;
                for(int j = 0; j < SIZE_REPLACEDWORD; j++)
                    *(origin_payload+index+j) = *(CHANGEWORD+j);
            }
        }
    }
}

void checkIfItExit(char* origin_payload,int size_origin_payload,int* code){
    if(size_origin_payload > SIZE_EXITWORD+1)
        return ;
    
    int check = TRUE;
    for(int index=0;index <SIZE_EXITWORD ;index++){
        check = check & (*(origin_payload+index) == *(EXITWORD+index));
        if(check == FALSE) break;
    }
    if(check ==TRUE)
        *code = EXIT;
}