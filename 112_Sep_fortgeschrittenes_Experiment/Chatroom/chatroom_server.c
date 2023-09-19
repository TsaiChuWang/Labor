#include "lib.h"
#define PORT 1999
#define MAX_CLIENTS 10

sem_t mutex; 
char ShareM[MAX]; // Share memory
int num_client=0; // total number of clients
int num_sent=0; // number of clients that the message has been sent
int new_message=0; // set to 1 when there is a new message, reset when all threads have sent
int sent_clientfd; //the client that sent the message will not receive the message it sent 
int exit_clientfd=-1;

char user_Namen[MAX_CLIENTS][20];
int user_Socket_ID[MAX_CLIENTS];
int user_Zahl = 0;

int soket_ID_sent = 4;

int send_mode =0 ;

struct connected_client{
	char* name;
	int socket_ID;
};

struct connected_client clients[MAX_CLIENTS];
int prestr(char* a,char* b){
	printf("A:%d B:%d\n",strlen(a),strlen(b));
	if(strlen(a)!=strlen(b)){
		// printf("no ame long\n");
		return 0;
	}else{
		for(int i=0;i<strlen(a);i++)
			if(*(a+i)!=*(b+i)){
				// printf("%d A:%c B:%c\n",i,*(a+i),*(b+i));
				return 0;
			}
	}	
	return 1;
}
void handle_message(char* buf,int* code){
	int len=0;
	for(int i=0;i<strlen(buf);i++){
		if(*(buf+i)==':'){
			len=i+2;
			break;
		}
	}
	char* message = (char*)malloc(sizeof(char)*(strlen(buf)-len-1));
	memset(message,'\0',sizeof(message));

	// printf("len=%d : %c, last = %d :%c a-b = %d\n",len,*(buf+len),strlen(buf),*(buf+strlen(buf)-2),strlen(buf)-len-2);
	for(int j=0;j<(strlen(buf)-len-1);j++){
		*(message+j)=*(buf+len+j);
	}
	*(message+strlen(buf)-len-1)='\0';
	// printf("message= %s\n",message);

	if(*message == '@')
	{
		char* key = "ALL";
		int check = 1;
		for(int i=1;i<4;i++){
			check = check & (*(message+i)==*(key+i-1));
			if(check == 0) break;
		}
			
		if(check == 1)
			send_mode=0 ; 
		else{
			int lengthname = 0;
			for(int i=1;i<strlen(message);i++){
				if(*(message+i) == ' '){
					lengthname=i;
					break;
				}
				if(*(message+i) == '\n'){
					lengthname=i;
					break;
				}
			}
			char* sendname=(char*)malloc(sizeof(char)*lengthname);
			for(int i=0;i<lengthname-1;i++)
				*(sendname+i)=*(message+i+1);
			*(sendname+lengthname-1)='\0';
			printf("Name = %s\n",sendname);

			send_mode= 1 ;

			int taeget_ID = soket_ID_sent;
			for(int i=0;i<user_Zahl;i++){
				struct connected_client p= *(clients+i);
				char* name =p.name;
				int socket_ID =p.socket_ID;

				if(prestr(sendname, name)==1)
					soket_ID_sent = p.socket_ID;
				// 	printf("name = %s,ID =%d, is name[%s] : False\n",name,socket_ID,sendname);
				// else
				// 	printf("name = %s,ID =%d, is name[%s] : True\n",name,socket_ID,sendname);
			}
		}
			 
			// printf("QQQQQQQQQQQQQQAAAAAAAAAAAAQQQQQQQQQQQQQQ\n");
	}
		// printf("QQQQQQQQQQQQQQAAAAAAAAAAAAQQQQQQQQQQQQQQ\n");
}



char* formattime(char* time_str){
	char* str = (char*)malloc(sizeof(char)*(strlen(time_str)));
	memset(str,'\0',sizeof(str));
	strcpy(str, time_str);
	*(str+strlen(time_str)-2)='\0';
	// printf("%s %d\n",str,strlen(time_str));
	return str;
}

void tagcheckName(char* buffer){
	char* name =(char*)malloc(sizeof(char)*strlen(buffer));
	int name_length =0;
	for(int index=1;index<strlen(buffer);index++){
		if(*(buffer+index) == ' ')
			break;
		
		*(name+name_length)=*(buffer+index);
		name_length ++;
	}
	*(name+name_length)='\0';
	printf("name = %s\n",name);
}

void* fsend(void* sockfd) 
{
	char buff[MAX]; 
	int sent=0; // set to one when this thread has already sent the new message
	for (;;) { 
		if(exit_clientfd == *(int*)sockfd){
			exit_clientfd=-1;
			break;
		}	
		if(new_message==0 && sent==1)	sent=0;	// reset sent
		else if(new_message==1 && sent==0 && sent_clientfd!=*(int*)sockfd){
			
			if(send_mode ==0){
				// send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
				send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
				bzero(buff, MAX);
				num_sent++;
				sent=1;	
				if(num_sent == num_client-1){ // last thread that hasn't sent runs
					bzero(ShareM, MAX); // reset Share memory
					num_sent=0;
					new_message=0;
				}
			}else if(send_mode == 1){
				send(soket_ID_sent, ShareM, sizeof(ShareM), 0); 
				bzero(buff, MAX);
				num_sent++;
				sent=1;	
				if(num_sent == num_client-1){ // last thread that hasn't sent runs
					bzero(ShareM, MAX); // reset Share memory
					num_sent=0;
					new_message=0;
				}
			}
			
		}
		else if(sent_clientfd==*(int*)sockfd && num_client==1 && new_message==1){ 
		// reset when there is only one client
			bzero(ShareM, MAX);
			num_sent=0;
			new_message=0;		
		}
		else{}
	}
}

void* frecv(void* sockfd) 
{
	char buff[MAX];
	char name[MAX];
	char* time_str;
	time_str=(char*)malloc(50);
	bzero(name,MAX);
    	int first=0;

	for(;;){		
		bzero(buff, MAX);
		recv(*(int*)sockfd, buff, sizeof(buff), 0); 
		if(buff[0]=='\0'){
			exit_clientfd= *(int*)sockfd; // record exited clientfd
			get_time(time_str);
			printf("\n%s-------%s exit-------\n",time_str,name);			
			break;
		}
		if(!first){//fisrt message is the name of client
			strcpy(name,buff);	
			get_time(time_str);
			char* c=formattime(time_str);
			printf("\x1B[1;31m\n[%s] Server accept the client %20s with %2d \n",c,name,*(int*)sockfd); 

			strcpy(*(user_Namen+user_Zahl), name);
			*(user_Socket_ID+user_Zahl)=*(int*)sockfd;

			struct connected_client p ={ .name=name,.socket_ID=*(int*)sockfd };
			*(clients+user_Zahl) =p;
			// *(clients+user_Zahl) = { .name=name,.socket_ID=*(int*)sockfd};

			user_Zahl ++;

			first=1;

			// soket_ID_sent = *(int*)sockfd;
			strcpy(buff, "0");
			strcat(buff, name);
			strcat(buff, " enters the chatroom !\n");			
			//continue;
		}
		else{
			get_time(time_str);
			char* c=formattime(time_str);
			// if(*buff == '@')
			// 	tagcheckName(buff);
			int code=0;
			printf("\n %s----%s",time_str, buff);
			handle_message(buff,&code);
		}

		sem_wait(&mutex); // semaphore wait
		while(new_message) // wait until all the threads sent the message (new_message=0)
			;
		sent_clientfd= *(int*)sockfd; // remember the client that sent the message
		strcpy(ShareM, buff); // Put the received message into Share memory
		new_message=1;  
		sem_post(&mutex); // semaphore signal
	}

	--num_client;	
//	printf("--num_client\n");
}

// Driver function 
int main() 
{ 
	int sockfd,  len; 
	int clientfds[MAX_CLIENTS];
	struct sockaddr_in servaddr, cliaddr; 
	
	// socket create and verification 
	sockfd = socket(AF_INET, SOCK_STREAM, 0); 
	if (sockfd == -1) { 
		printf("-------socket creation failed-------\n"); 
		exit(0); 
	} 
	else
		printf("-------Socket successfully created-------\n"); 
	bzero(&servaddr, sizeof(servaddr)); 

	// assign IP, PORT 
	servaddr.sin_family = AF_INET; 
	servaddr.sin_addr.s_addr = htonl(INADDR_ANY); 
	servaddr.sin_port = htons(PORT); 

	// Binding newly created socket to given IP and verification 
	if ((bind(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr))) != 0) { 
		printf("-------Socket bind failed-------\n"); 
		exit(0); 
	} 
	else
		printf("-------Socket successfully binded-------\n"); 

	// Now server is ready to listen and verification 
	if ((listen(sockfd, MAX_CLIENTS)) != 0) { 
		printf("-------Listen failed-------\n"); 
		exit(0); 
	} 
	else
		printf("-------Server listening-------\n"); 
	len = sizeof(cliaddr); 
	
	pthread_t thr_send, thr_recv;
	sem_init(&mutex, 0, 1); 

	while(1){
		// Accept the data packet from client and verification 
		int* clientfd = clientfds + num_client;
		
		*clientfd = accept(sockfd, (struct sockaddr*)&cliaddr, &len); 
		if (*clientfd < 0) { 
			printf("-------Server acccept failed-------\n"); 
			exit(0); 
		} 
		else{
			
			if(num_client >= MAX_CLIENTS){
				printf("-------Reach the max number of clients!-------\n");
			}
			else{
				++num_client;
				
				pthread_create(&thr_send, NULL, fsend, (void*) clientfd);
				pthread_create(&thr_recv, NULL, frecv, (void*) clientfd);
			}
			
		}
	}

	bzero(ShareM, MAX);

	sem_destroy(&mutex);
	pthread_join(thr_send, NULL);
	pthread_join(thr_recv, NULL);
	
	// After chatting close the socket 
	close(sockfd); 
} 
