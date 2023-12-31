#include "lib.h"

#define MAX_CLIENTS 100
#define MAX_GROUPS 100
#define MAX_GROUPS_MEMBER 100
#define MAX_NAME_LENGTH 15

sem_t mutex; 
char ShareM[MAX]; // Share memory
int num_client=0; // total number of clients
int num_sent=0; // number of clients that the message has been sent
int new_message=0; // set to 1 when there is a new message, reset when all threads have sent
int sent_clientfd; //the client that sent the message will not receive the message it sent 
int exit_clientfd=-1;

/* Structure of client */
struct client
{
	char* cleint_name;
	int client_socket;
	int client_avaliable;

	int* client_group_category;
	int zahl_client_group_category;
};
struct client connected_clients[MAX_CLIENTS];
int zahl_connected_client =0;
int maximum_socket_ID = 0;

/* Structure of groups */
struct group
{
	char* group_name;

	int* mitglied_socke_IDs;
	int zahl_mitglied;
};
struct group chat_groups[MAX_GROUPS];
int zahl_chat_groups =0;

int target_chat_group = 0;
int target_recieved_client = 0;

int sending_mode = 0;	/* Send mode to clients */

/* Get time string */
char* format_time_string(char* time_str);

/* Check if it tag all */
int checkIfTagALL(char* message);

/* Comapre two string are same or not */
int compareStringsIsSame(char* string_A, char* string_B);

/* find target socket_ID by client name*/
int findTargetClientByName(char* name);

/* check if it command means join/create a group */
int checkIfJoinCreateGroup(char* message);

/* Distinguish if it create or join the group */
int distinguishIfJoinCreateGroup(char* group_name);

/* find target client name by client socket_ID*/
char* findTargetClientBySocketID(int socket_ID);

/* Check if socket_ID in the group */
int checkIfSocketIDInGroup(int socket_ID, struct group target_group);

/* Get group name from message */
char* getGroupNameByMessage(char* message, int end_index){
	char* group_name = (char*)malloc(sizeof(char)*(end_index+1));
	memset(group_name, '\0',sizeof(group_name));
	for(int index=0;index<end_index;index++)
		*(group_name+index)=*(message+index);
	return group_name;
}

/* find group index by group name */
int findCahtGroupIndexByName(char* group_name){
	if(zahl_chat_groups == 0)
		return NOT_FOUND;

	for(int index=0;index<zahl_chat_groups;index++){
		struct group temperatur_group = *(chat_groups+index);
		if(compareStringsIsSame(temperatur_group.group_name,group_name) == TRUE)
			return index;
	}
	return NOT_FOUND;
}

/* Find the client structure */
int findTargetClientSturctureByID(int socket_ID){
	for(int index=0;index<zahl_connected_client;index++){
		struct client temperatur_client = *(connected_clients+index);
		if(temperatur_client.client_socket == socket_ID)
			return index;
	}
	return NOT_FOUND;
}

/* Reocord Create a group */
void recordCreateGroupInfomation(int transmitter,char* group_name){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");
	
    fprintf(file, "%s [%15s:%3d] Mode :%2d client %15s[%2d] wants create a group named %15s, now has %2d groups.\n", format_time_string(time_str), findTargetClientBySocketID(transmitter), transmitter, sending_mode, findTargetClientBySocketID(transmitter), transmitter, group_name, zahl_chat_groups);
	printf(KMAG"%s [%15s:%3d] Mode :%2d client %15s[%2d] wants create a group named %15s, now has %2d groups.\n", format_time_string(time_str), findTargetClientBySocketID(transmitter), transmitter, sending_mode, findTargetClientBySocketID(transmitter), transmitter, group_name, zahl_chat_groups);

    fclose(file);
}

/* Reocord Join the group */
void recordJoinGroupInfomation(int transmitter,char* group_name){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");
	
    fprintf(file, "%s [%15s:%3d] Mode :%2d client %15s[%2d] wants to join a group named %15s, now has %2d groups.\n", format_time_string(time_str), findTargetClientBySocketID(transmitter), transmitter, sending_mode, findTargetClientBySocketID(transmitter), transmitter, group_name, zahl_chat_groups);
	printf(KCYN"%s [%15s:%3d] Mode :%2d client %15s[%2d] wants to join a group named %15s, now has %2d groups.\n", format_time_string(time_str), findTargetClientBySocketID(transmitter), transmitter, sending_mode, findTargetClientBySocketID(transmitter), transmitter, group_name, zahl_chat_groups);

	int group_index = findCahtGroupIndexByName(group_name);
	struct group target_group = *(chat_groups+group_index);
	fprintf(file, "This group has %3d members :",target_group.zahl_mitglied);
	printf("This group has %3d members :",target_group.zahl_mitglied);
	for(int index=0;index<target_group.zahl_mitglied;index++){
		if(index == target_group.zahl_mitglied-1){
			fprintf(file, " %s[%3d]\n",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
			printf(" %s[%3d]\n",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
		}else{
			fprintf(file, " %s[%3d],", findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
			printf(" %s[%3d],",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
		}
	}

    fclose(file);
}

/* Handle the payload */
void payloadHandling(int transmitter,char* payload,char* time_str){
	// printf(WHITE_L"[%15s]Get payload from transmitter : %2d, %s",format_time_string(time_str), transmitter, payload);

	/* Get proccessed data name and message */
	char* name;
	char* message;
	int erst_mode = ALL;
	
	int target_index = 0;
	for(int index=0;index<strlen(payload);index++)
		if(*(payload+index) == ':'){
			target_index = index;
			break;
		}
	
	name = (char*)malloc(sizeof(char)*(target_index+1));
	memset(name, '\0', sizeof(name));
	for(int index=0; index < target_index;index ++)
		*(name+index) = *(payload+index);

	int start = (*(payload+target_index+2) == '@' || *(payload+target_index+2) =='!') ? 1 : 0;
	message = (char*)malloc(sizeof(char)*(strlen(payload)-target_index-1));
	memset(message, '\0', sizeof(message));
	for(int index=target_index+2+start; index < strlen(payload)-1;index ++)
		*(message+index-(target_index+2+start)) = *(payload+index);

	// printf("convert name : %15s, message: %20s, erst_mode = %d \n",name, message, erst_mode);

	if(*(payload+target_index+2) == '@') erst_mode = 1;
	if(*(payload+target_index+2) == '!') erst_mode = 2;

	if(erst_mode == 0){
		sending_mode = ALL;
		return;
	}

	if(erst_mode == 1){
		/* Check if @ALL */
		int if_all = checkIfTagALL(message);
		if(if_all == TRUE){
			// printf(KGRY"Mode : %d, because %15s @ALL\n", ALL, name);
			sending_mode = ALL;
			return;
		}

		/* Find tagName */
		int tag_index = -1;
		for(int index=0;index<strlen(message);index++)
			if(*(message+index) == ' '){
				tag_index = index;
				break;
			}
		if(tag_index == -1){
			sending_mode = ALL;
			return;
		}

		char* tag_name = (char*)malloc(sizeof(char)*(tag_index+1));;
		memset(tag_name, '\0', sizeof(tag_name));
		for(int index=0;index<tag_index;index++)
			*(tag_name+index)=*(message+index);

		int tag_client_socket_ID = findTargetClientByName(tag_name);
		if(tag_client_socket_ID == NOT_FOUND){
			printf(KGRY"Mode : %d, because %15s @%s : socket_ID NOT_FOUND \n", TAG, name, tag_name);
			sending_mode = ALL;
			return;
		}
		target_recieved_client = tag_client_socket_ID;
		// printf(KGRY"Mode : %d, because %15s @%s, socket_ID : %d\n", TAG, name, tag_name, target_recieved_client);
		sending_mode = TAG;
	}

	if(erst_mode == 2){
		/* check if send message or join/create*/
		int if_join_or_create = checkIfJoinCreateGroup(message);

		if(if_join_or_create == NOT_FOUND){
			/* Find out if it is join or create a group */
			int join_or_create = distinguishIfJoinCreateGroup(message);

			if(join_or_create == NOT_FOUND){
				int* mitglied = (int*)malloc(sizeof(int)*MAX_GROUPS_MEMBER);
				memset(mitglied, -1, sizeof(mitglied));
				*mitglied = transmitter;

				struct group new_created_group = {
					.group_name = message,
					.mitglied_socke_IDs = mitglied,
					.zahl_mitglied = 1
				};
				*(chat_groups+zahl_chat_groups)=new_created_group;
				zahl_chat_groups = zahl_chat_groups+1;

				int client_index = findTargetClientSturctureByID(transmitter);
				struct client target_client = *(connected_clients+client_index);

				int* client_group_category = target_client.client_group_category;
				int category_index = target_client.zahl_client_group_category;
				*(client_group_category + category_index) = zahl_chat_groups - 1;
				category_index = category_index + 1;
				target_client.client_group_category = client_group_category;
				target_client.zahl_client_group_category = category_index;
				*(connected_clients+client_index) = target_client;

				recordCreateGroupInfomation(transmitter, message);
				// printf(KGRN"Mode :%2d client %15s[%2d] wants create a group named %15s, now has %2d groups.\n",CREATE_GROUP, name, transmitter, message, zahl_chat_groups);
				sending_mode = CREATE_GROUP;
				return;
			}
			
			struct group joined_group= *(chat_groups+join_or_create);
			// printf(KGRN"client %15s[%2d] joins to the group named %15s in index = %3d \n",name, transmitter, joined_group.group_name, join_or_create);
			
			*(joined_group.mitglied_socke_IDs + joined_group.zahl_mitglied) = transmitter;
			joined_group.zahl_mitglied = joined_group.zahl_mitglied + 1; 
			
			*(chat_groups+join_or_create) = joined_group;

			// printf("This group has %3d members :",joined_group.zahl_mitglied);
			// for(int index=0;index<joined_group.zahl_mitglied;index++)
			// 	if(index == joined_group.zahl_mitglied-1)
			// 		printf(" %s[%3d]\n",findTargetClientBySocketID(*(joined_group.mitglied_socke_IDs+index)),*(joined_group.mitglied_socke_IDs+index));
			// 	else printf(" %s[%3d],",findTargetClientBySocketID(*(joined_group.mitglied_socke_IDs+index)),*(joined_group.mitglied_socke_IDs+index));

			recordJoinGroupInfomation(transmitter, message);

			target_chat_group = join_or_create;
			sending_mode = JOIN_GROUP;
			return;
		}

		char* group_name = getGroupNameByMessage(message, if_join_or_create);
		target_chat_group = findCahtGroupIndexByName(group_name);

		int client_index = findTargetClientSturctureByID(transmitter);
		struct client target_client = *(connected_clients+client_index);

		int* client_group_category = target_client.client_group_category;
		int category_index = target_client.zahl_client_group_category;
		*(client_group_category + category_index) = zahl_chat_groups - 1;
		category_index = category_index + 1;
		target_client.client_group_category = client_group_category;
		target_client.zahl_client_group_category = category_index;
		*(connected_clients+client_index) = target_client;

		sending_mode = SEND_MESSAGE_GROUP;
		printf("client %15s[%2d] wants send message to a group[%15s:%3d],from index %3d\n",name, transmitter, group_name, target_chat_group, if_join_or_create);
	}
}

/* Record Server Information */
void recordServerInfomation(char* message){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");
    fprintf(file, "%s %s", format_time_string(time_str), message);
	printf(KBLU"%s %s", format_time_string(time_str), message);

    fclose(file);
}

/* Reocord client connections */
void recordClientConnectionsInfomation(char* client_name, int client_socket_ID){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");
    fprintf(file, "%s [%15s:%3d] A client named [%10s] with ID = %2d is entered in chatroom, now clients : %3d !\n", format_time_string(time_str), client_name, client_socket_ID, client_name, client_socket_ID, zahl_connected_client);
	printf(KBLU_L"%s [%15s:%3d] A client named [%10s] with ID = %2d is entered in chatroom, now clients : %3d !\n", format_time_string(time_str), client_name, client_socket_ID, client_name, client_socket_ID, zahl_connected_client);

    fclose(file);
}

/* Reocord tag ALL connections */
void recordTagALLInfomation(char* message, int reciever){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");

	char* name;
	int target_index = 0;
	for(int index=0;index<strlen(message);index++)
		if(*(message+index) == ':'){
			target_index = index;
			break;
		}
	
	name = (char*)malloc(sizeof(char)*(target_index+1));
	memset(name, '\0', sizeof(name));
	for(int index=0; index < target_index;index ++)
		*(name+index) = *(message+index);
	
    fprintf(file, "%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);
	printf(KGRN"%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);

    fclose(file);
}

/* Reocord tag someone connections */
void recordTagSomeoneInfomation(char* message, int reciever){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");

	char* name;
	int target_index = 0;
	for(int index=0;index<strlen(message);index++)
		if(*(message+index) == ':'){
			target_index = index;
			break;
		}
	
	name = (char*)malloc(sizeof(char)*(target_index+1));
	memset(name, '\0', sizeof(name));
	for(int index=0; index < target_index;index ++)
		*(name+index) = *(message+index);
	
    fprintf(file, "%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);
	printf(KYEL"%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);

    fclose(file);
}

/* Reocord talk to the group connections */
void recordTalkToGroupInfomation(char* message, int reciever){
	char* time_str = (char*)malloc(sizeof(char)*TIME_LENGTH);
	get_time(time_str);

	FILE* file = fopen(FILENAME, "a");

    if (file == NULL) 
        perror("Error opening the file");

	char* name;
	int target_index = 0;
	for(int index=0;index<strlen(message);index++)
		if(*(message+index) == ':'){
			target_index = index;
			break;
		}
	
	name = (char*)malloc(sizeof(char)*(target_index+1));
	memset(name, '\0', sizeof(name));
	for(int index=0; index < target_index;index ++)
		*(name+index) = *(message+index);
	
	fprintf(file, "%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);
    // fprintf(file, "%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);
	printf(WHITE_L"%s [%15s:%3d] - [%15s:%3d] %50s", format_time_string(time_str), name, findTargetClientByName(name), findTargetClientBySocketID(reciever), reciever, message);

    fclose(file);
}

void* fsend(void* sockfd) 
{
	char buffer[MAX]; 
	int sent=0; // set to one when this thread has already sent the new message
	while(TRUE) { 
		if(exit_clientfd == *(int*)sockfd){
			exit_clientfd=-1;
			break;
		}	
		if(new_message==0 && sent==1)	sent=0;	// reset sent
		else if(new_message==1 && sent==0 && sent_clientfd!=*(int*)sockfd){
			struct group target_group;
			int is_in_group;

			switch (sending_mode)
			{
				case ALL:
					recordTagALLInfomation(ShareM, *(int*)sockfd);
					send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
					bzero(buffer, MAX);
					num_sent++;
					sent=1;	
					if(num_sent == num_client-1){ // last thread that hasn't sent runs
						bzero(ShareM, MAX); // reset Share memory
						num_sent=0;
						new_message=0;
					}
					break;
				case TAG:
					if(*(int*)sockfd == target_recieved_client){
						recordTagSomeoneInfomation(ShareM, *(int*)sockfd);
						// printf(KRED_L"Mode :%2d, send to client : %2d :%s\n",TAG, target_recieved_client, ShareM);
						send(target_recieved_client , ShareM, sizeof(ShareM), 0); 
						bzero(buffer, MAX);
						num_sent++;
						sent=1;	
						if(num_sent == num_client-1){ // last thread that hasn't sent runs
							bzero(ShareM, MAX); // reset Share memory
							num_sent=0;
							new_message=0;
						}
					}
					break;
				case CREATE_GROUP:
					send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
					bzero(buffer, MAX);
					num_sent++;
					sent=1;	
					if(num_sent == num_client-1){ // last thread that hasn't sent runs
						bzero(ShareM, MAX); // reset Share memory
						num_sent=0;
						new_message=0;
					}
					break;
				case JOIN_GROUP:
					target_group = *(chat_groups + target_chat_group);
					// printf(KGRN"Mode :%2d, now broadcast to group %3d named %s\n", sending_mode, target_chat_group, target_group.group_name);

					// printf("Share memory :%s\n",ShareM);
					// printf("This group has %3d members :",target_group.zahl_mitglied);
					// for(int index=0;index<target_group.zahl_mitglied;index++)
					// 	if(index == target_group.zahl_mitglied-1)
					// 		printf(" %s[%3d]\n",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
					// 	else printf(" %s[%3d],",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));

					is_in_group = checkIfSocketIDInGroup(*(int*)sockfd, target_group);
					if(is_in_group != NOT_FOUND){
						send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
						bzero(buffer, MAX);
						num_sent++;
						sent=1;	
						if(num_sent == num_client-1){ // last thread that hasn't sent runs
							bzero(ShareM, MAX); // reset Share memory
							num_sent=0;
							new_message=0;
						}
					}
					break;
				case SEND_MESSAGE_GROUP:
					target_group = *(chat_groups + target_chat_group);
					// printf(KYEL"Mode :%2d, now broadcast to group %3d named %s\n", sending_mode, target_chat_group, target_group.group_name);

					// send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
					// bzero(buffer, MAX);
					// num_sent++;
					// sent=1;	
					// if(num_sent == num_client-1){ // last thread that hasn't sent runs
					// 	bzero(ShareM, MAX); // reset Share memory
					// 	num_sent=0;
					// 	new_message=0;
					// }

					// printf("Share memory :%s\n",ShareM);
					// printf("This group has %3d members :",target_group.zahl_mitglied);
					// for(int index=0;index<target_group.zahl_mitglied;index++)
					// 	if(index == target_group.zahl_mitglied-1)
					// 		printf(" %s[%3d]\n",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));
					// 	else printf(" %s[%3d],",findTargetClientBySocketID(*(target_group.mitglied_socke_IDs+index)),*(target_group.mitglied_socke_IDs+index));

					is_in_group = checkIfSocketIDInGroup(*(int*)sockfd, target_group);
					if(is_in_group != NOT_FOUND){
						recordTalkToGroupInfomation(ShareM, *(int*)sockfd);
						send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
						bzero(buffer, MAX);
						num_sent++;
						sent=1;	
						if(num_sent == num_client-1){ // last thread that hasn't sent runs
							bzero(ShareM, MAX); // reset Share memory
							num_sent=0;
							new_message=0;
						}
						// printf("client %15s[%d] is in the group %s\n", findTargetClientBySocketID(*(int*)sockfd), *(int*)sockfd, target_group.group_name);
					}else{
						num_sent=0;
						new_message=0;
						if(num_sent == num_client-1){ // last thread that hasn't sent runs
							bzero(ShareM, MAX); // reset Share memory
							num_sent=0;
							new_message=0;
						}
						// printf("client %15s[%d] is not in the group %s\n", findTargetClientBySocketID(*(int*)sockfd), *(int*)sockfd, target_group.group_name);
					}
					break;
			default:
				send(*(int*)sockfd, ShareM, sizeof(ShareM), 0); 
				bzero(buffer, MAX);
				num_sent++;
				sent=1;	
				if(num_sent == num_client-1){ // last thread that hasn't sent runs
					bzero(ShareM, MAX); // reset Share memory
					num_sent=0;
					new_message=0;
				}
				break;
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
	char buffer[MAX];
	char name[MAX];
	char* time_str;
	time_str=(char*)malloc(50);
	bzero(name,MAX);
    int erst_komm=0;

	while(TRUE){		
		bzero(buffer, MAX);
		recv(*(int*)sockfd, buffer, sizeof(buffer), 0); 
		if(buffer[0]=='\0'){
			exit_clientfd= *(int*)sockfd; // record exited clientfd
			get_time(time_str);
			printf("\n%s-------%s exit-------\n",time_str,name);			
			break;
		}
		if(!erst_komm){//fisrt message is the name of client
			strcpy(name,buffer);	
			get_time(time_str);
			erst_komm = TRUE;
			strcat(buffer, " enters the chatroom !\n");		
			
			int* category = (int*)malloc(sizeof(int)*MAX_GROUPS);
			memset(category, -1, sizeof(category));
			struct client new_connection = {
				.cleint_name = name,
				.client_avaliable = TRUE,
				.client_socket = *(int*)sockfd,
				.client_group_category = category,
				.zahl_client_group_category = 0
			};
			*(connected_clients + zahl_connected_client) = new_connection;
			zahl_connected_client +=1;

			recordClientConnectionsInfomation(name, *(int*)sockfd);
		}
		else{
			get_time(time_str);
			// printf("\n%s----%s",time_str, buffer);
			payloadHandling(*(int*)sockfd, buffer, time_str);
		}

		sem_wait(&mutex); // semaphore wait
		while(new_message) // wait until all the threads sent the message (new_message=0)
			;
		sent_clientfd= *(int*)sockfd; // remember the client that sent the message
		strcpy(ShareM, buffer); // Put the received message into Share memory
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
		recordServerInfomation("Socket creation failed !\n");
		exit(0); 
	} else recordServerInfomation("Socket successfully created !\n");
	bzero(&servaddr, sizeof(servaddr)); 

	// assign IP, PORT 
	servaddr.sin_family = AF_INET; 
	servaddr.sin_addr.s_addr = htonl(INADDR_ANY); 
	servaddr.sin_port = htons(PORT); 

	// Binding newly created socket to given IP and verification 
	if ((bind(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr))) != 0) { 
		recordServerInfomation("Socket bind failed !\n");
		exit(0); 
	} else recordServerInfomation("Socket successfully binded !\n");

	// Now server is ready to listen and verification 
	if ((listen(sockfd, MAX_CLIENTS)) != 0) { 
		recordServerInfomation("Listen failed !\n");
		exit(0); 
	} else recordServerInfomation("Server listening !\n");
	len = sizeof(cliaddr); 
	
	pthread_t thr_send, thr_recv;
	sem_init(&mutex, 0, 1); 

	while(1){
		// Accept the data packet from client and verification 
		int* clientfd = clientfds + num_client;
		
		*clientfd = accept(sockfd, (struct sockaddr*)&cliaddr, &len); 
		if (*clientfd < 0) { 
			recordServerInfomation("Server acccept failed !\n");
			exit(0); 
		} 
		else{
			
			if(num_client >= MAX_CLIENTS)
				recordServerInfomation("Reach the max number of clients !\n");
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

char* format_time_string(char* time_str){
	char* time_string = (char*)malloc(sizeof(char)*(strlen(time_str)));
	memset(time_string,'\0',sizeof(time_string));
	strcpy(time_string, time_str);
	*(time_string+strlen(time_str)-2)='\0';
	return time_string;
}

int checkIfTagALL(char* message){
	int if_all = TRUE;
	for(int index = 0;index < ALLWORD_LENGTH;index++){
		if_all = if_all & (*(ALLWORD+index)==*(message+index));

		if(if_all == FALSE)
			return FALSE;
	}
	return TRUE;
}

int compareStringsIsSame(char* string_A, char* string_B){
	if(strlen(string_A)!=strlen(string_B))
		return FALSE;
	
	for(int index =0;index <strlen(string_A);index++)
		if(*(string_A+index)!=*(string_B+index))
			return FALSE;
	return TRUE;
}

int findTargetClientByName(char* name){
	if(zahl_connected_client == 0)
		return NOT_FOUND;
	
	for(int index=0;index< zahl_connected_client;index++){
		struct client temperatur_client = *(connected_clients+index);
		if(compareStringsIsSame(temperatur_client.cleint_name, name) == TRUE && temperatur_client.client_avaliable == TRUE)
			return temperatur_client.client_socket;
	}

	return NOT_FOUND;
}

int checkIfJoinCreateGroup(char* message){
	for(int index=0;index<strlen(message);index++)
		if(*(message+index)==' ')
			return index;
	return NOT_FOUND;
}

int distinguishIfJoinCreateGroup(char* group_name){
	if(zahl_chat_groups == 0)
		return NOT_FOUND;
	
	for(int index =0;index < zahl_chat_groups;index++){
		struct group temperatur_group = *(chat_groups+index);
		if(compareStringsIsSame(temperatur_group.group_name, group_name) ==TRUE)
			return index;
	}
	return NOT_FOUND;
}

char* findTargetClientBySocketID(int socket_ID){
	if(zahl_connected_client == 0)
		return NAME_NOT_FOUND;
	
	for(int index=0;index< zahl_connected_client;index++){
		struct client temperatur_client = *(connected_clients+index);
		if(temperatur_client.client_socket == socket_ID)
			return temperatur_client.cleint_name;
	}
	return NAME_NOT_FOUND;
}

int checkIfSocketIDInGroup(int socket_ID, struct group target_group){
	for(int index=0;index < target_group.zahl_mitglied;index++)
		if(*(target_group.mitglied_socke_IDs+index) == socket_ID )
			return index;

	return NOT_FOUND;
}
