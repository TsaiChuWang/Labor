#include <stdio.h> 
#include <netdb.h> 
#include <netinet/in.h> 
#include <stdlib.h> 
#include <string.h> 
#include <sys/socket.h> 
#include <sys/types.h>
#include <sys/time.h>
#include <pthread.h> 
#include <semaphore.h> 
#include <unistd.h>
#include <arpa/inet.h>
#define MAX 80

#define TRUE 1
#define FALSE 0
#define NOT_FOUND -1
#define NAME_NOT_FOUND ""

#define ALL 0
#define TAG 1
#define CREATE_GROUP 2
#define JOIN_GROUP 3

#define PORT 2009

#define ALLWORD "ALL"
#define ALLWORD_LENGTH 3

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

void get_time(char* time_str){
	struct timeval now;
	gettimeofday(&now,NULL);
	strcpy(time_str,ctime(&now.tv_sec));
}
