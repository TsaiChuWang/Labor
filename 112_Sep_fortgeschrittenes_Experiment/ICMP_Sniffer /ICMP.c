#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/ip_icmp.h>
#include <arpa/inet.h>

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
#define TRUE 1

int main(int argc, char *argv[]){

    int socket_descriptor;	// Socket 描述符
	char buffer[1024];  // 緩衝區
	struct iphdr *iphdrptr;	// pointer of IPv4 header structure 
	struct icmphdr *icmphdrptr;	// pointer of ICMP header structure

	// [1] 開一個 IPv4 的 RAW Socket , 並且準備收取 ICMP 封包
    socket_descriptor = socket(PF_INET, SOCK_RAW, IPPROTO_ICMP);   // IPv4 協定, socket 的類型 : SOCK_RAW, 協議 : ICMP
    if(socket_descriptor < 0){
        perror("socket");   // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式
    }

	printf(KGRN"Raw Socket has created already, use \"ping [domain name/IP address]\" to trigger the process.\n");

	while(TRUE){
		// 清空 buffer
        memset(buffer, 0, sizeof(buffer));

		// [2] 接收來自目標主機的 Echo Reply
        int recieve_packet_size = recv(socket_descriptor, buffer, sizeof(buffer), 0);  
        if(recieve_packet_size < 1){
            perror("recv");
            exit(-1);
        }

        // 取出 IP Header
        iphdrptr = (struct iphdr*)buffer;

        uint16_t IP_hdr = iphdrptr->ihl * 4; // bytes to bits
        uint8_t ttl = iphdrptr->ttl;    // time-to-live
        uint8_t protocol = iphdrptr->protocol;	// protocol code

        printf(KCYN"IPv4 : IP_hdr : %3d paket_size : %8d protocol : %2d ttl : %4d\n", IP_hdr, recieve_packet_size, protocol, ttl);
        
		// 取出 ICMP Header
        icmphdrptr = (struct icmphdr*)(buffer+(iphdrptr->ihl)*4);   // ihl :  32 位字中的互聯網標頭長度 (IHL)

        uint8_t type = icmphdrptr->type; // ICMP 消息類型
        uint8_t code = icmphdrptr->code;    // 特定ICMP消息類型的代碼
        uint16_t checksum = icmphdrptr->checksum;  // Checksum for the ICMP packet
        uint16_t un;    // 未使用的數據或標識符和序列號

        printf(KBLU"ICMP : Type   : ");
		printf(KRED_L"%3d", type);
		printf(KBLU" checksum   : %8d protocol : %2d ttl : %4d\n",  checksum, protocol, ttl);
	}

    close(socket_descriptor); // 關閉 socket
    return EXIT_SUCCESS;
}