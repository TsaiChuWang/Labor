#define ALLE_GLEICHE_KAPAZITÄT

#include "../Enthalten/Aufbau.h"
#include "../Enthalten/Prüfung.h"
#include <stdio.h>
#include <stdlib.h>

int adj[6][6]={{0,1,1,0,0,0},
					 {1,0,0,1,0,0},
					 {1,0,0,0,1,0},
					 {0,1,0,0,0,1},
					 {0,0,1,0,0,1},
					 {0,0,0,1,1,0}
					};

int list[6][6]={{0,1,1,0,0,0},
					 {1,0,0,1,0,0},
					 {1,0,0,0,1,0},
					 {0,1,0,0,0,1},
					 {0,0,1,0,0,1},
					 {0,0,0,1,1,0}
					};

int main()
{
	int x,y,i,j,k,h,link,node,c;
	int con=0;
	FILE *f1;
	f1=fopen("1515.lp","w+");
	fprintf(f1,"min r\n");
	fprintf(f1,"Subject to \n");
	c=77;
	for(x=1;x<=12;x++){
		for(y=1;y<=12;y++){
		fprintf(f1," %dBl%d(h%d)",c,x,y);
		if(y==12){
			fprintf(f1," - r <= 0\n");
		}
		else{
			fprintf(f1," + ");
		}
		}
		


		for(i=1;i<=6;i++){
			h=1;
			for(j=1;j<=6;j++){
				for(k=1;k<=6;k++){
					if(j!=k&&adj[j-1][k-1]==1){
						if(i!=j&&i!=k){
							fprintf(f1," Bl%d(h%d) + A%d,%dl%d - A%d,%dl%d >= 0\n",x,h,i,j,x,i,k,x);
							h++;
						}
						else if(i!=j){
							fprintf(f1," Bl%d(h%d) + A%d,%dl%d >= 0\n",x,h,i,j,x);
							h++;
						}
						else if(i!=k){
							fprintf(f1," Bl%d(h%d) - A%d,%dl%d >= 0\n",x,h,i,k,x);
							h++;
						}
					}
				}
			}
		}
		
		for(i=1;i<=6;i++){
			for(j=1;j<=6;j++){
				if(i!=j){
				fprintf(f1," %dA%d,%dl%d + %dS_p_%d,%d(l%d) - %dS_m_%d,%d(l%d) -f%d,%d(l%d) >= 0\n",c,i,j,x,c,i,j,x,c,i,j,x,i,j,x);
				}
			}
		}
		
		for(i=1;i<=6;i++){
			for(j=1;j<=6;j++){
				if(i!=j){
					if(i<j){
						fprintf(f1," %dS_m_%d,%d(l%d) - %dS_p_%d,%d(l%d)",i,i,j,x,j,i,j,x);
					}
					else if(i>j){
						fprintf(f1," %dS_m_%d,%d(l%d) - %dS_p_%d,%d(l%d)",j,i,j,x,i,i,j,x);
					}
				if(i==6&&j==5){
				}
				else{
					fprintf(f1," +");
				}
				}
				if(i==6&&j==6){
				fprintf(f1," >=0\n");
				}
				
			}
		}
		
	}
	
	link=1;
	for(i=0;i<=5;i++){
		for(j=0;j<=5;j++){
			if(list[i][j]==1){
				list[i][j]=link;
				link++;
			}
		}
	}
	
	
	for(node=1;node<=6;node++){
		
		//source
		h=0;
		
				
				for(i=1;i<=6;i++){
					if(node!=i){
						for(j=1;j<=6;j++){
						if(list[node-1][j-1]!=0){
						if(h==0){
							h=1;
						}
						else if(h==1){
							fprintf(f1," +");
						}
						fprintf(f1," f%d,%d(l%d) - f%d,%d(l%d)",node,i,list[node-1][j-1],node,i,list[j-1][node-1]);
					}
				}
						fprintf(f1," = 1\n");
						h=0;
			}
		}
		//dst
		h=0;
		for(i=1;i<=6;i++){
					if(node!=i){
						for(j=1;j<=6;j++){
						if(list[node-1][j-1]!=0){
						if(h==0){
							h=1;
						}
						else if(h==1){
							fprintf(f1," +");
						}
						fprintf(f1," f%d,%d(l%d) - f%d,%d(l%d)",i,node,list[node-1][j-1],i,node,list[j-1][node-1]);
					}
				}
						fprintf(f1," = -1\n");
						h=0;
			}
		}
		// line
		//mid
		h=0;
				for(k=1;k<=6;k++){			
					for(i=1;i<=6;i++){
						if(node!=i&&node!=k&&i!=k){
						for(j=1;j<=6;j++){
						if(list[node-1][j-1]!=0){
						
							if(h==0){
								h=1;
							}
							else if(h==1){
								fprintf(f1," +");
							}
							fprintf(f1," f%d,%d(l%d) - f%d,%d(l%d)",k,i,list[node-1][j-1],k,i,list[j-1][node-1]);
						}
					}
					fprintf(f1," = 0\n");
					h=0;
				}
				
			}
		}
		

	}
	
	fprintf(f1,"Bounds\n");
	for(x=1;x<=12;x++){
		for(y=1;y<=12;y++){
			fprintf(f1,"Bl%d(h%d) >= 0\n",x,y);
		}
	}
	for(k=1;k<=12;k++){
		for(x=1;x<=6;x++){
			for(y=1;y<=6;y++){
				if(x!=y){
					fprintf(f1,"S_p_%d,%d(l%d) > 0\n",x,y,k);
				}
			}
		}
	}

	for(k=1;k<=12;k++){
		for(x=1;x<=6;x++){
			for(y=1;y<=6;y++){
				if(x!=y){
					fprintf(f1,"S_m_%d,%d(l%d) >= 0\n",x,y,k);
				}
			}
		}
	}

	for(x=1;x<=12;x++){
		for(i=1;i<=6;i++){
			for(j=1;j<=6;j++){
				if(i!=j){
				fprintf(f1," f%d,%d(l%d) >= 0\n",i,j,x);
				fprintf(f1," f%d,%d(l%d) <= 1\n",i,j,x);
				}
			}
		}
	}

	fprintf(f1,"End\n");
	printf("end\n");
}
