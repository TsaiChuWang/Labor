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
#define BUFF_LEN 1024

 void handle_udp_msg(int fd)
 {
    char buffer[BUFF_LEN];    //接收緩衝區，1024字節
    socklen_t length;
    int num;
    struct sockaddr_in client_addr;    // clent_addr用於記錄發送方的地址信息

    while(1)
     {
        memset(buffer, 0, BUFF_LEN); // 初始化 buffer 為 0
        length = sizeof(client_addr);   // 發送方的地址長度

        // 接收來自發送方（client）的數據
        num = recvfrom(fd, buffer, BUFF_LEN, 0, (struct sockaddr*)&client_addr, &length);    // recvfrom 是擁塞函數，沒有數據就一直擁塞
        if(num == -1) // 一旦接收失敗
        {
            printf(KMAG"recieve data fail!\n");
            return ;
        }

        printf(KYEL"client: %25s\n" ,buffer);    //ㄒ打印client發過來的信息
        memset(buffer, 0, BUFF_LEN); // 初始化 buffer 為 0

        sprintf(buffer,"I have recieved %5d bytes data !\n" , num);    //回覆client
        printf(KCYN"server : %s\n" ,buffer);    // 打印自己發送的信息給到 terminal
        
        sendto(fd, buffer, BUFF_LEN, 0, (struct sockaddr*)&client_addr, length);    //發送信息給client，注意使用了clent_addr結構體指針
     }
 }


 /*
     server:
             socket-->bind-->recvfrom-->sendto- ->close
 */

 int main ( int argc, char * argv[])
 {
    int server_dentifier, ret;  // socket 文件描述符, 
    struct sockaddr_in server_addr; // Server 的 IP address

    server_dentifier = socket(AF_INET, SOCK_DGRAM, 0); // AF_INET:IPV4; SOCK_DGRAM: UDP
    if(server_dentifier < 0)
    {
        perror("socket");   // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式;
    }

    memset(&server_addr, 0, sizeof(server_addr));   // 初始化 server_addr 為 0

    server_addr.sin_family = AF_INET;   // IPv4
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY); // IP地址，需要進行網絡序轉換，INADDR_ANY：本地地址
    server_addr.sin_port = htons(SERVER_PORT);    //端口號，需要網絡序轉換

    ret = bind(server_dentifier, (struct sockaddr*)&server_addr, sizeof(server_addr));
    if(ret < 0) 
    {
        perror("socket bind fail");   // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式;
    }

    handle_udp_msg(server_dentifier);     //處理接收到的數據


    close(server_dentifier);    // 關閉 udp socket
    return 0 ;
}