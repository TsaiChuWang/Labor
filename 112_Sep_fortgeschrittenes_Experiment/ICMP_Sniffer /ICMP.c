#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/if_ether.h>
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
#define FLASE 0
#define FAILURE -1

#define MAXIMUM_PACKET_SIZE 1024

void packetHandler(unsigned char* buffer, int size);

int main() {
    int raw_socket_sniffer;
    unsigned char buffer[MAXIMUM_PACKET_SIZE]; // Maximum packet size

    raw_socket_sniffer = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL)); // Create a raw socket sniffer
    if (raw_socket_sniffer == FAILURE) {    // handel socket created failure
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    printf(KGRN"ICMP Sniffer : socket has been created.\n");

    while (TRUE) {  // endless loop
        int data_size = recv(raw_socket_sniffer, buffer, sizeof(buffer), 0);    // Recieve packet data to buffer
        if (data_size == -1) {  // handel packet recieved failure
            perror("Packet capture error");
            close(raw_socket_sniffer);
            exit(EXIT_FAILURE);
        }

        packetHandler(buffer, data_size);   // Process the packet
        memset(buffer, 0, sizeof(buffer));  // 清空 buffer
    }

    close(raw_socket_sniffer);  // close the socket
    return 0;
}

void packetHandler(unsigned char* buffer, int size) {   // Process the packet
    struct ether_header* eth_header = (struct ether_header*)buffer;
    struct icmphdr* icmpheader_pointer;
    struct iphdr* ipheader_pointer;

    if(ntohs(eth_header->ether_type) == ETHERTYPE_IP) {    // If protocol is IPv4
        ipheader_pointer = (struct iphdr*)(buffer + sizeof(struct ether_header));   // packet of IPv4

        if(ipheader_pointer->protocol == IPPROTO_ICMP){
            uint16_t IP_hdr = ipheader_pointer->ihl * 4; // Header Length (4 bits) *4
            uint8_t ttl = ipheader_pointer->ttl;    // time -to live
            uint8_t protocol = ipheader_pointer->protocol;  //protocol number

            printf(KCYN"IPv4 : IP_hdr : %3d paket_size : %6d protocol : %6d TTL : %4d\n", IP_hdr, size, protocol, ttl); // Print information from IPv4 header

            icmpheader_pointer = (struct icmphdr*)(buffer + sizeof(struct ether_header) + (ipheader_pointer->ihl * 4)); // packet of ICMP

            uint8_t type = icmpheader_pointer->type; // ICMP 消息類型
            uint8_t code = icmpheader_pointer->code;    // 特定ICMP消息類型的代碼
            uint16_t checksum = icmpheader_pointer->checksum;  // Checksum for the ICMP packet
            // checksum = checksum((unsigned short*)&checksum, sizeof(checksum));
            uint16_t un;    // 未使用的數據或標識符和序列號
            uint16_t _id = ntohs(icmpheader_pointer->un.echo.id);   // idntifier
            uint16_t _sequence = ntohs(icmpheader_pointer->un.echo.sequence);   //sequence number

            printf(KBLU_L"ICMP : Type   : ");   // print information from ICMP packet
            printf(KRED_L"%3d", type);  // highlight type
            printf(KBLU_L" checksum   : %6d id       : %6d seq : %4d\n", checksum, _id, _sequence);
        }
    }
}