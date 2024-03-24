#define ALLE_GLEICHE_KAPAZITÄT

#include "../Enthalten/Aufbau.h"
#include "../Enthalten/Prüfung.h"   // MATERIAL AUF PRÜFUNG
#include <stdio.h>
#include <stdlib.h>

int main()
{
	int kant, kant_andere,i,j,k,schalter,link,node,h;
    
    // Öffnen Sie die Textdatei
	FILE *dateizeiger;
	dateizeiger = fopen("../Datei/"DATEI_NAME".lp","w+");
	fprintf(dateizeiger,"min r\n");
	fprintf(dateizeiger,"Subject to \n");

	for(int kant=1;kant<= ANZAHL_KANTEN;kant++){ // Für jeden Umrande

        // min r,\forall e\in E \sum_{h\in E}cap(h)\pi_e(h)\leq r
		for(int kant_andere=1;kant_andere<= ANZAHL_KANTEN;kant_andere++){
		    fprintf(dateizeiger," %dpi_e%02d(h%02d)",KAPAZITÄT, kant, kant_andere);
            if(kant_andere == ANZAHL_KANTEN)
                fprintf(dateizeiger," - r <=  0\n");
            else fprintf(dateizeiger," + ");
		}
        fprintf(dateizeiger, "\n");
		
        // Constraints 1: \forall i,j\in N,i\neq j p_e(i,j)+s^+_e(i,j)-s^-_e(i,j)=f_{ij}(e)/cap(e)
		for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++){
			schalter = 1;
			for(int knote_j=1;knote_j<= ANZAHL_KNOTEN;knote_j++)
				for(int knote_k=1;knote_k<= ANZAHL_KNOTEN;knote_k++)
					if(knote_j!= knote_k && BOGEN[knote_j-1][knote_k-1] == RICHTIG){
						if(knote_i!=knote_j && knote_i!=knote_k){
							fprintf(dateizeiger," pi_e%02d(h%02d) + p(%02d_%02d)_e%02d - p(%02d_%02d)_e%02d >=  0\n", kant, schalter, knote_i, knote_j, kant, knote_i, knote_k, kant);
							schalter++;
						}
						else if(knote_i!=knote_j){
							fprintf(dateizeiger," pi_e%02d(h%02d) + p(%02d_%02d)_e%02d >=  0\n", kant, schalter, knote_i, knote_j, kant);
							schalter++;
						}
						else if(knote_i!= knote_k){
							fprintf(dateizeiger," pi_e%02d(h%02d) - p(%02d_%02d)_e%02d >=  0\n", kant, schalter, knote_i, knote_k, kant);
							schalter++;
						}
					}
		}
		fprintf(dateizeiger, "\n");

        // Constriants 2 : \forall i,j\in N,i\neq j \pi_e(edge-of(a)) +p_e(i,j)-p_e(i,k)\geq0
		for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
			for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++)
				if(knote_i!=knote_j)
				    fprintf(dateizeiger," %d p(%02d_%02d)_e%02d + %d s(%02d_%02d)_e%02d_plus - %ds(%02d_%02d)_e%02d_minus -f_%02d_%02d(e%02d) >=  0\n", KAPAZITÄT, knote_i, knote_j, kant, KAPAZITÄT, knote_i, knote_j, kant, KAPAZITÄT, knote_i, knote_j, kant, knote_i, knote_j, kant);
        fprintf(dateizeiger, "\n");

        // Constraint 3 : \sum_{ij}(s_e^-(i,j)a_{ij}-s_e^+(i,j)b_{ij})\geq0
		for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
			for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++){
                if(knote_i<knote_j)
					fprintf(dateizeiger," %ds(%02d_%02d)_e%02d_minus - %ds(%02d_%02d)_e%02d_plus", knote_i, knote_i, knote_j, kant, knote_j, knote_i, knote_j, kant);
					
				if(knote_i>knote_j)
					fprintf(dateizeiger," %ds(%02d_%02d)_e%02d_minus - %ds(%02d_%02d)_e%02d_plus", knote_j, knote_i, knote_j, kant, knote_i, knote_i, knote_j, kant);
					
				if(!(knote_i == ANZAHL_KNOTEN && knote_j == (ANZAHL_KNOTEN-1)) && (knote_i != knote_j))
                    fprintf(dateizeiger," +");
				
				if(i == ANZAHL_KNOTEN && j == ANZAHL_KNOTEN)
				    fprintf(dateizeiger," >= 0\n");
            }
		fprintf(dateizeiger, "\n\n");
        
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
	
	
	for(node = 1;node<= ANZAHL_KNOTEN;node++){
		
		//source
		h = 0;
		
				
				for(i = 1;i<= ANZAHL_KNOTEN;i++){
					if(node!= i){
						for(j = 1;j<= ANZAHL_KNOTEN;j++){
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
		for(i = 1;i<= ANZAHL_KNOTEN;i++){
					if(node!= i){
						for(j = 1;j<= ANZAHL_KNOTEN;j++){
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
				for(k = 1;k<= ANZAHL_KNOTEN;k++){			
					for(i = 1;i<= ANZAHL_KNOTEN;i++){
						if(node!= i&&node!= k&&i!= k){
						for(j = 1;j<= ANZAHL_KNOTEN;j++){
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
			fprintf(dateizeiger,"pi_e%02d(h%02d) >=  0\n", kant, kant_andere);
		}
	}
	for(k = 1;k<= ANZAHL_KANTEN;k++){
		for(kant = 1;kant<= ANZAHL_KNOTEN;kant++){
			for(kant_andere = 1;kant_andere<= ANZAHL_KNOTEN;kant_andere++){
				if(kant!= kant_andere){
					fprintf(dateizeiger,"s(%02d_%02d)_e%02d_plus > 0\n", kant, kant_andere,k);
				}
			}
		}
	}

	for(k = 1;k<= ANZAHL_KANTEN;k++){
		for(kant = 1;kant<= ANZAHL_KNOTEN;kant++){
			for(kant_andere = 1;kant_andere<= ANZAHL_KNOTEN;kant_andere++){
				if(kant!= kant_andere){
					fprintf(dateizeiger,"s(%02d_%02d)_e%02d_minus >=  0\n", kant, kant_andere,k);
				}
			}
		}
	}

	for(kant = 1;kant<= ANZAHL_KANTEN;kant++){
		for(i = 1;i<= ANZAHL_KNOTEN;i++){
			for(j = 1;j<= ANZAHL_KNOTEN;j++){
				if(i!= j){
				fprintf(dateizeiger," f_%02d_%02d(e%02d) >=  0\n",i,j, kant);
				fprintf(dateizeiger," f_%02d_%02d(e%02d) <=  1\n",i,j, kant);
				}
			}
		}
	}

	fprintf(dateizeiger,"End\n");
	printf("end\n");
}
