#define ALLE_GLEICHE_KAPAZITÄT

#define ELF_KNOTEN_COST239

#ifdef EINS
	#include "../Enthalten/Erstes_Modul.h"   // MATERIAL
#endif
#ifdef NSFNET
	#include "../Enthalten/NSFNET.h"   // NSFNET
#endif
#ifdef USA26
	#include "../Enthalten/USA-26.h"   // USA26
#endif
#ifdef USA28
	#include "../Enthalten/USA-28.h"   // USA28
#endif
#ifdef ELF_KNOTEN_COST239
	#include "../Enthalten/ELF_KNOTEN_COST239.h"   // 11-node cost 239
#endif

#include "../Enthalten/Aufbau.h"

#include <stdio.h>
#include <stdlib.h>

int main()
{
	int kant, kant_andere,i,j,k,knote,h;
    int schalter;

	druckinformationstopologie();

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
				    fprintf(dateizeiger," %d p(%02d_%02d)_e%02d + %d s(%02d_%02d)_e%02d_plus - %d s(%02d_%02d)_e%02d_minus - f_%02d_%02d(e%02d) >=  0\n", KAPAZITÄT, knote_i, knote_j, kant, KAPAZITÄT, knote_i, knote_j, kant, KAPAZITÄT, knote_i, knote_j, kant, knote_i, knote_j, kant);
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
				
				if(knote_i == ANZAHL_KNOTEN && knote_j == ANZAHL_KNOTEN)
				    fprintf(dateizeiger," >= 0\n");
            }
		fprintf(dateizeiger, "\n\n");
	}
    fprintf(dateizeiger, "\n\n");

    // Flow conservation : Zuberbeitung
	int verknupfüng = 1;
	for(int knote_i=0;knote_i<=(ANZAHL_KNOTEN-1);knote_i++)
		for(int knote_j = 0;knote_j<=(ANZAHL_KNOTEN-1);knote_j++)
			if(LISTE[knote_i][knote_j] == RICHTIG){
				LISTE[knote_i][knote_j] = verknupfüng;
				verknupfüng++;
			}
	fprintf(dateizeiger, "\n\n");
	
	// Flow conservation : constraints
    schalter = 0;
	for(int knote=1;knote<= ANZAHL_KNOTEN;knote++){
		// Quelle
		schalter = 0;
		for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
			if(knote!=knote_i){
				for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++)
					if(LISTE[knote-1][knote_j-1]!=0){
						if(schalter == 0)
							schalter = 1;
						else if(schalter == 1)
							fprintf(dateizeiger," + ");
						
						fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)", knote, knote_i,LISTE[knote-1][knote_j-1], knote, knote_i,LISTE[knote_j-1][knote-1]);
					}
				
				fprintf(dateizeiger,"  =  1\n");
				schalter = 0;
			}
		 // Ziel
		schalter = 0;
		for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
			if(knote!=knote_i){
				for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++)
					if(LISTE[knote-1][knote_j-1]!= 0){
						if(schalter == 0)
							schalter = 1;
						else if(schalter == 1)
							fprintf(dateizeiger," + ");
				
						fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)", knote_i, knote, LISTE[knote-1][knote_j-1], knote_i, knote, LISTE[knote_j-1][knote-1]);
					}
				
				fprintf(dateizeiger,"  = -1\n");
				schalter = 0;
			}
		
		// Mitte
		schalter = 0;
		for(int knote_k=1;knote_k<=ANZAHL_KNOTEN;knote_k++)		
			for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
				if(knote!= knote_i && knote!=knote_k && knote_i!=knote_k){
					for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++){
						if(LISTE[knote-1][knote_j-1]!= 0){
							if(schalter == 0)
								schalter = 1;
							else if(schalter == 1)
								fprintf(dateizeiger," + ");
							
							fprintf(dateizeiger," f_%02d_%02d(e%02d) - f_%02d_%02d(e%02d)", knote_k, knote_i, LISTE[knote-1][knote_j-1], knote_k, knote_i,LISTE[knote_j-1][knote-1]);
						}
					}
					fprintf(dateizeiger,"  =  0\n");
					schalter = 0;
				}
		fprintf(dateizeiger, "\n");
    }
    fprintf(dateizeiger, "\n\n");
	
    // Decision constraints (Entscheidungsbeschränkungen)
	fprintf(dateizeiger,"Bounds\n");

    // pi_e(h)
	for(int kant = 1;kant<=ANZAHL_KANTEN;kant++)
		for(int kant_andere = 1;kant_andere<=ANZAHL_KANTEN;kant_andere++)
			fprintf(dateizeiger,"pi_e%02d(h%02d) >=  0\n", kant, kant_andere);
		
	// /forall kant\in E, knote_i knote_j \in N, i\neq j
    for(int kant = 1;kant<=ANZAHL_KANTEN;kant++)
        for(int knote_i=1;knote_i<=ANZAHL_KNOTEN;knote_i++)
			for(int knote_j=1;knote_j<=ANZAHL_KNOTEN;knote_j++)
                if(knote_i!=knote_j){
                    fprintf(dateizeiger,"s(%02d_%02d)_e%02d_plus  >= 0\n", knote_i, knote_j, kant); // s_e^+(i,j)
                    fprintf(dateizeiger,"s(%02d_%02d)_e%02d_minus >= 0\n", knote_i, knote_j, kant); // s_e^-(i,j)
                    fprintf(dateizeiger," f_%02d_%02d(e%02d) >=  0\n", knote_i, knote_j, kant); // f_{st}(e)>=0
				    fprintf(dateizeiger," f_%02d_%02d(e%02d) <=  1\n", knote_i, knote_j, kant); // f_{st}(e)<=1
                }

	fprintf(dateizeiger,"\nEnd\n");
	// druckinformationstopologie();
}