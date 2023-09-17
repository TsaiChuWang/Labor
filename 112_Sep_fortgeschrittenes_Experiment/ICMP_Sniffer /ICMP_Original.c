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

// 做 checksum 運算, 驗證資料有無毀損
unsigned short checksum(unsigned short *buffer, int buffersize){
    unsigned long sum = 0xffff; // 用 0xffff 初始化總和

    while(buffersize > 1){  // 以 16 bits（2 words）塊的形式處理緩衝區
        sum += *buffer; // 將 buffer 指向的 16 位值添加到 sum 中
        buffer++;   // 移至緩衝區中的下一個 16 位值
        buffersize -= 2;    // 將剩餘緩衝區大小減少 2 words
    }

    if(buffersize == 1) // 如果剩下奇數 word ，則將其作為 16 位值添加到總和中
        sum += *(unsigned char*)buffer; 

    // 處理任何進位（溢出）並將它們折疊回總和中
    sum = (sum & 0xffff) + (sum >> 16);
    sum = (sum & 0xffff) + (sum >> 16);

    return ~sum;    // 返回最終和的補碼（bitwise NOT）作為校驗和
}

int main(int argc, char *argv[]){

    int socket_dentifier;
    struct icmphdr hdr;
    struct sockaddr_in addr;    // sockaddr_in 的結構用來存取網路相關的應用， in 指的是 internet，sockaddr_in 專門用來存 IPv4 的相關地址
    int num;
    char buffer[1024];  // 緩衝區
    struct icmphdr *icmphdrptr;
    struct iphdr *iphdrptr;

    int count = 10;

    
    if(argc < 2){  // 如果沒有給定參數（目標 IP 位址）
        printf("argument lost: correct command type : { sudo %s [IPADDR] } .\n", argv[0]); // 提示你缺少參數
        exit(-1);   // 以 -1 結束程式
    }

    addr.sin_family = PF_INET; // 2 bytes 地址族 : IPv4

    // 將使用者輸入的 IP 轉成 network order
    num = inet_pton(PF_INET, argv[1], &addr.sin_addr);  // 將 IP 地址從人類可讀的格式轉換為網絡順序格式
    if(num < 0){    //如果轉換過程中發生錯誤，返回-1
        perror("inet_pton");    // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式
    }

    // 開一個 IPv4 的 RAW Socket , 並且準備收取 ICMP 封包
    socket_dentifier = socket(PF_INET, SOCK_RAW, IPPROTO_ICMP);   // IPv4 協定, socket 的類型 : SOCK_RAW, 協議 : ICMP
    if(socket_dentifier < 0){
        perror("socket");   // 打印帶有錯誤描述的錯誤消息
        exit(-1);   // 以 -1 結束程式
    }

    // 清空結構內容
    memset(&hdr, 0, sizeof(hdr)); // 填充 hdr 的前n個字符為 0

    // 初始化 ICMP Header
    hdr.type = ICMP_ECHO;   // 指定 ICMP 消息的類型為 ICMP Echo Request 消息類型，用於 ping 遠程主機
    hdr.code = 0;   // 通常提供與 ICMP 消息類型相關的附加信息，但對於 ICMP Echo Request，它通常設置為 0
    hdr.checksum = 0;   // 校驗和字段，最初校驗和設置為 0，表示尚未計算

    // 在發送或接收多個 ping 請求時幫助識別和匹配請求和響應
    hdr.un.echo.id = 0; 
    hdr.un.echo.sequence = 0;   

    // 計算出 checksum
    hdr.checksum = checksum((unsigned short*)&hdr, sizeof(hdr));

    count = atoi(argv[3]);  // packet count

    for(int index = 0; index < count; index ++){
        
        // 將定義好的 ICMP Header 送到目標主機
        num = sendto(socket_dentifier, (char*)&hdr, sizeof(hdr), 0, (struct sockaddr*)&addr, sizeof(addr));
        if(num < 1){
            perror("sendto");   // 打印帶有錯誤描述的錯誤消息
            exit(-1);   // 以 -1 結束程式
        }
        printf(KYEL"We have sended an ICMP packet to %s\n", argv[1]);   // Yellow

        // 清空 buffer
        memset(buffer, 0, sizeof(buffer));

        // printf(KGRN"Waiting for ICMP echo...\n");

        // 接收來自目標主機的 Echo Reply
        int recieve_packet_size = recv(socket_dentifier, buffer, sizeof(buffer), 0);  
        if(recieve_packet_size < 1){
            perror("recv");
            exit(-1);
        }

        // 取出 IP Header
        iphdrptr = (struct iphdr*)buffer;

        uint16_t IP_hdr = iphdrptr->ihl * 4; // Version (4 bits) and Header Length (4 bits)
        uint8_t ttl = iphdrptr->ttl;    // ttl
        uint8_t protocol = iphdrptr->protocol;

        printf(KCYN"IPv4 : IP_hdr : %3d paket_size : %4d protocol : %2d ttl : %4d\n", IP_hdr, recieve_packet_size, protocol, ttl);
        
        // 取出 ICMP Header
        icmphdrptr = (struct icmphdr*)(buffer+(iphdrptr->ihl)*4);   // ihl :  32 位字中的互聯網標頭長度 (IHL)

        uint8_t type = icmphdrptr->type; // ICMP 消息類型
        uint8_t code = icmphdrptr->code;    // 特定ICMP消息類型的代碼
        uint16_t checksum = icmphdrptr->checksum;  // Checksum for the ICMP packet
        // checksum = checksum((unsigned short*)&checksum, sizeof(checksum));
        uint16_t un;    // 未使用的數據或標識符和序列號

        printf(KMAG"ICMP : Type   : %3d checksum   : %4d protocol : %2d ttl : %4d\n", type, checksum, protocol, ttl);
        // printf(KCYN"IPv4 : IP_hdr : %3d paket_size : %4d protocol : %2d ttl : %4d\n", IP_hdr, recieve_packet_size, protocol, ttl);
        

        // int header_length = ip->ip_hl; // header length

        
    
        // 判斷 ICMP 種類
        // switch(type){
        //     case 3: // 該主機是不可以 ping 到的
        //         printf(KGRY"The host %.20s is a unreachable purpose!\n", argv[1]);
        //         printf(KGRY"The ICMP type is %5d\n", type);
        //         printf(KGRY"The ICMP code is %5d\n", icmphdrptr->code);
        //         break;
        //     case 8: // 該主機是可以 ping 到的
        //         printf(KCYN"The host %.20s is alive!\n", argv[1]);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Type", type);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Code", code);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Checksum", checksum);

        //         printf(KCYN"The ICMP %14s is %5d\n", "TTL", ttl);
        //         printf(KCYN"The ICMP %14s is %5d\n", "header length", header_length);
        //         break;
        //     case 0: // 該主機是可以 ping 到的
        //         printf(KGRN_L"The host %.20s is alive!\n", argv[1]);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Type", type);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Code", code);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Checksum", checksum);

        //         printf(KCYN"The ICMP %14s is %5d\n", "TTL", ttl);
        //         printf(KCYN"The ICMP %14s is %5d\n", "Header length", header_length);

        //         break;  // 其他情況
        //         printf(KMAG"Another situations!\n");
        //         printf(KMAG"The ICMP type is %5d\n", type);
        //         printf(KMAG"The ICMP code is %5d\n", icmphdrptr->code);
        //         break;
        // }
    }

    close(socket_dentifier); // 關閉 socket
    return EXIT_SUCCESS;
}