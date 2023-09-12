#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <string.h>

 #define SERVER_PORT 8888
 #define BUFF_LEN 1024

 void handle_udp_msg( int fd)
 {
     char buf[BUFF_LEN];    //接收緩衝區，1024字節
     socklen_t len;
     int count;
     struct sockaddr_in clent_addr;    // clent_addr用於記錄發送方的地址信息
     while( 1 )
     {
          memset(buf, 0 , BUFF_LEN);
          len = sizeof(clent_addr);
          count = recvfrom(fd, buf, BUFF_LEN, 0 , (struct sockaddr*)&clent_addr, &len);    // recvfrom是擁塞函數，沒有數據就一直擁塞
         if (count == - 1 )
         {
              printf( " recieve data fail!\n ");
             return ;
         }
          printf( " client:%s\n " ,buf);    //打印client發過來的信息
          memset(buf, 0 , BUFF_LEN);
          sprintf(buf, " I have recieved % d bytes data !\n " , count);    //回复client
          printf( " server:%s\n " ,buf);    //打印自己發送的信息給
          sendto(fd, buf, BUFF_LEN, 0 , ( struct sockaddr* )&clent_addr, len);    //發送信息給client，注意使用了clent_addr結構體指針

     }
 }


 /*
     server:
             socket-->bind-->recvfrom-->sendto- ->close
 */

 int main ( int argc, char * argv[])
 {
    int server_fd, ret;
    struct sockaddr_in ser_addr;

    server_fd = socket(AF_INET, SOCK_DGRAM, 0); // AF_INET:IPV4;SOCK_DGRAM:UDP
    if (server_fd < 0 )
    {
        printf( " create socket fail!\n " );
        return - 1 ;
    }

    memset(&ser_addr, 0 , sizeof ( ser_addr));
    ser_addr.sin_family = AF_INET;
    ser_addr.sin_addr.s_addr = htonl(INADDR_ANY); // IP地址，需要進行網絡序轉換，INADDR_ANY：本地地址
    ser_addr.sin_port = htons(SERVER_PORT);    //端口號，需要網絡序轉換

    ret = bind(server_fd, (struct sockaddr*)&ser_addr, sizeof(ser_addr));
    if (ret < 0 )
    {
        printf( "socket bind fail!\n" );
        return - 1 ;
    }

    handle_udp_msg(server_fd);     //處理接收到的數據

    close(server_fd);
    return 0 ;
}