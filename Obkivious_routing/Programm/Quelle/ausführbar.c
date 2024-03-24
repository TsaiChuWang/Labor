#define ALLE_GLEICHE_KAPAZITÄT

#include "../Enthalten/Aufbau.h"
#include "../Enthalten/Prüfung.h"   // MATERIAL AUF PRÜFUNG
#include <stdio.h>
#include <stdlib.h>

int main()
{
	int kant,kant_andere,i,j,k,h,link,node;

    // Öffnen Sie die Textdatei
	FILE *dateizeiger;
	dateizeiger = fopen("../Datei/"DATEI_NAME".lp","w+");
	fprintf(dateizeiger,"min r\n");
	fprintf(dateizeiger,"Subject to \n");

	for(int kant=1;kant<= ANZAHL_KANTEN;kant++){ // Für jeden Umrande
    
        // min r,\forall e\in E \sum_{h\in E}cap(h)\pi_e(h)\leq r
		for(int kant_andere=1;kant_andere<= ANZAHL_KANTEN;kant_andere++){
		    fprintf(dateizeiger," %dpi_e%02d(h%02d)",KAPAZITÄT,kant,kant_andere);
            if(kant_andere == ANZAHL_KANTEN)
                fprintf(dateizeiger," - r <=  0\n");
            else fprintf(dateizeiger," + ");
		}
		
		for(i = 1;i<= 6;i++){
			h = 1;
			for(j = 1;j<= 6;j++){
				for(k = 1;k<= 6;k++){
					if(j!= k&&BOGEN[j-1][k-1] == 1){
						if(i!= j&&i!= k){
							fprintf(dateizeiger," pi_e%02d(h%02d) + p(%02d_%02d)_e%02d - p(%02d_%02d)_e%02d >=  0\n",kant,h,i,j,kant,i,k,kant);
							h++;
						}
						else if(i!= j){
							fprintf(dateizeiger," pi_e%02d(h%02d) + p(%02d_%02d)_e%02d >=  0\n",kant,h,i,j,kant);
							h++;
						}
						else if(i!= k){
							fprintf(dateizeiger," pi_e%02d(h%02d) - p(%02d_%02d)_e%02d >=  0\n",kant,h,i,k,kant);
							h++;
						}
					}
				}
			}
		}
		
		for(i = 1;i<= 6;i++){
			for(j = 1;j<= 6;j++){
				if(i!= j){
				fprintf(dateizeiger," %d p(%02d_%02d)_e%02d + %d s(%02d_%02d)_e%02d_plus - %ds(%02d_%02d)_e%02d_minus -f_%02d_%02d(e%02d) >=  0\n",KAPAZITÄT,i,j,kant,KAPAZITÄT,i,j,kant,KAPAZITÄT,i,j,kant,i,j,kant);
				}
			}
		}
		
		for(i = 1;i<= 6;i++){
			for(j = 1;j<= 6;j++){
				if(i!= j){
					if(i<j){
						fprintf(dateizeiger," %ds(%02d_%02d)_e%02d_minus - %ds(%02d_%02d)_e%02d_plus",i,i,j,kant,j,i,j,kant);
					}
					else if(i>j){
						fprintf(dateizeiger," %ds(%02d_%02d)_e%02d_minus - %ds(%02d_%02d)_e%02d_plus",j,i,j,kant,i,i,j,kant);
					}
				if(i == 6&&j == 5){
				}
				else{
					fprintf(dateizeiger," +");
				}
				}
				if(i == 6&&j == 6){
				fprintf(dateizeiger," >= 0\n");
				}
				
			}
		}
		
	}
	
	link = 1;
	for(i = 0;i<= 5;i++){
		for(j = 0;j<= 5;j++){
			if(LISTE[i][j] == 1){
				LISTE[i][j] = link;
				link++;
			}
		}
	}
	
	
	for(node = 1;node<= 6;node++){
		
		//source
		h = 0;
		
				
				for(i = 1;i<= 6;i++){
					if(node!= i){
						for(j = 1;j<= 6;j++){
						if(LISTE[node-1][j-1]!= 0){
						if(h == 0){
							h = 1;
						}
						else if(h == 1){
							fprintf(dateizeiger," +");
						}
						fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)",node,i,LISTE[node-1][j-1],node,i,LISTE[j-1][node-1]);
					}
				}
						fprintf(dateizeiger,"  =  1\n");
						h = 0;
			}
		}
		//dst
		h = 0;
		for(i = 1;i<= 6;i++){
					if(node!= i){
						for(j = 1;j<= 6;j++){
						if(LISTE[node-1][j-1]!= 0){
						if(h == 0){
							h = 1;
						}
						else if(h == 1){
							fprintf(dateizeiger," +");
						}
						fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)",i,node,LISTE[node-1][j-1],i,node,LISTE[j-1][node-1]);
					}
				}
						fprintf(dateizeiger,"  =  -1\n");
						h = 0;
			}
		}
		//mid
		h = 0;
				for(k = 1;k<= 6;k++){			
					for(i = 1;i<= 6;i++){
						if(node!= i&&node!= k&&i!= k){
						for(j = 1;j<= 6;j++){
						if(LISTE[node-1][j-1]!= 0){
						
							if(h == 0){
								h = 1;
							}
							else if(h == 1){
								fprintf(dateizeiger," +");
							}
							fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)",k,i,LISTE[node-1][j-1],k,i,LISTE[j-1][node-1]);
						}
					}
					fprintf(dateizeiger,"  =  0\n");
					h = 0;
				}
				
			}
		}
		

	}
	
	fprintf(dateizeiger,"Bounds\n");
	for(kant = 1;kant<= ANZAHL_KANTEN;kant++){
		for(kant_andere = 1;kant_andere<= ANZAHL_KANTEN;kant_andere++){
			fprintf(dateizeiger,"pi_e%02d(h%02d) >=  0\n",kant,kant_andere);
		}
	}
	for(k = 1;k<= ANZAHL_KANTEN;k++){
		for(kant = 1;kant<= 6;kant++){
			for(kant_andere = 1;kant_andere<= 6;kant_andere++){
				if(kant!= kant_andere){
					fprintf(dateizeiger,"s(%02d_%02d)_e%02d_plus > 0\n",kant,kant_andere,k);
				}
			}
		}
	}

	for(k = 1;k<= ANZAHL_KANTEN;k++){
		for(kant = 1;kant<= 6;kant++){
			for(kant_andere = 1;kant_andere<= 6;kant_andere++){
				if(kant!= kant_andere){
					fprintf(dateizeiger,"s(%02d_%02d)_e%02d_minus >=  0\n",kant,kant_andere,k);
				}
			}
		}
	}

	for(kant = 1;kant<= ANZAHL_KANTEN;kant++){
		for(i = 1;i<= 6;i++){
			for(j = 1;j<= 6;j++){
				if(i!= j){
				fprintf(dateizeiger," f_%02d_%02d(e%02d) >=  0\n",i,j,kant);
				fprintf(dateizeiger," f_%02d_%02d(e%02d) <=  1\n",i,j,kant);
				}
			}
		}
	}

	fprintf(dateizeiger,"End\n");
	printf("end\n");
}
