#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <string.h>

#ifndef _DEBUG_COLOR_
#define _DEBUG_COLOR_
    #define KDRK "\x1B[0;30m"
    #define KGRY "\x1B[1;30m"
    #define KRED "\x1B[0;31m"
    #define KRED_L "\x1B[1;31m"
    #define KGRN "\x1B[0;32m"
    #define KGRN_L "\x1B[1;32m"
    #define KYEL "\x1B[0;33m"
    #define KYEL_L "\x1B[1;33m"
    #define KBLU "\x1B[0;34m"
    #define KBLU_L "\x1B[1;34m"
    #define KMAG "\x1B[0;35m"
    #define KMAG_L "\x1B[1;35m"
    #define KCYN "\x1B[0;36m"
    #define KCYN_L "\x1B[1;36m"
    #define WHITE "\x1B[0;37m"
    #define WHITE_L "\x1B[1;37m"
    #define RESET "\x1B[0m"
#endif

#define SERVER_PORT 1996
#define BUFF_LEN 512
#define SERVER_IP "127.0.0.1"

 void udp_msg_sender(int fd, struct sockaddr* dst_address,char *message)
 {
    socklen_t length;
    struct sockaddr_in src_address; // 來源 IP address
    while(1)
    {
        char buffer[BUFF_LEN];
        strncpy(buffer, message, sizeof(BUFF_LEN)); // 將指針中的字符複製到數組
        buffer[strlen(message)] = '\0'; // 字串結尾

        length = sizeof(*dst_address);
        printf(KYEL"client : %s \n",message);   //打印自己發送的信息
        sendto(fd, buffer, BUFF_LEN, 0, dst_address, length);
        
        memset(buffer, 0, BUFF_LEN);    // 初始化 buffer 為 0
        recvfrom(fd, buffer, BUFF_LEN, 0, (struct sockaddr*)&src_address, &length);   //接收來自server的信息
        printf(KCYN"server : %25s\n" ,buffer);
        sleep(1);   //一秒發送一次消息
     }
 }

 /*
     client:
             socket-->sendto-->revcfrom-->close
 */

 int main( int argc, char * argv[])
 {
    int client_dentifier;
    struct sockaddr_in server_addr;

    client_dentifier = socket(AF_INET, SOCK_DGRAM, 0);
    if(client_dentifier < 0)
    {
        perror("socket");   // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式;
     }

    memset(&server_addr , 0, sizeof(server_addr));  // 初始化 server_addr 為 0
    
    server_addr.sin_family = AF_INET;
    // server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);   //注意網絡序轉換
    server_addr.sin_port = htons(SERVER_PORT);   //注意網絡序轉換

    udp_msg_sender(client_dentifier, (struct sockaddr*)& server_addr, argv[1]);

    close(client_dentifier);    // 關閉 udp socket
    return  0 ;
}