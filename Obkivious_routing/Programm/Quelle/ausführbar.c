#define ALLE_GLEICHE_KAPAZITÄT

#include "../Enthalten/Aufbau.h"
#include "../Enthalten/Prüfung.h"
#include <stdio.h>
#include <stdlib.h>

// gcc ausführbar.c -o ../Ausführung/ausführbar

int main(void){
    // printf("Prüfung\n");

    // min r 
    // constraints for each edges
    // flow conservation
    // bounds

    // Öffnen Sie die Textdatei
    FILE *dateizeiger;
    dateizeiger=fopen("../Datei/"DATEI_NAME".lp","w+");
	
    // min r,\forall e\in E \sum_{h\in E}cap(h)\pi_e(h)\leq r
    fprintf(dateizeiger,"min r\n");
	fprintf(dateizeiger,"Subject to \n");

    for(int kant_eins=1; kant_eins<=ANZAHL_KANTEN; kant_eins++){
        for(int kant_zwei=1; kant_zwei<=ANZAHL_KANTEN; kant_zwei++){
            fprintf(dateizeiger, "%d pi_e%02d(h%02d)", KAPAZITÄT, kant_eins, kant_zwei);
            if(kant_zwei == ANZAHL_KANTEN)
                fprintf(dateizeiger, " <= r\n");
            else fprintf(dateizeiger, " + ");
        }
    }

    fprintf(dateizeiger, "\n\n");

    // Constraints 1: \forall i,j\in N,i\neq j p_e(i,j)+s^+_e(i,j)-s^-_e(i,j)=f_{ij}(e)/cap(e)
    for(int kant=1; kant<=ANZAHL_KANTEN; kant++){ // kant = e
        for(int knote_i = 1; knote_i<=ANZAHL_KNOTEN; knote_i++) //knote_i = i
            for(int knote_j = 1; knote_j<=ANZAHL_KNOTEN; knote_j++)  // knote_j = j
                if(knote_i != knote_j)
                    fprintf(dateizeiger, "%d p_e%02d(%02d_%02d) + %d s_e%02d_plus(%02d_%02d) - %d s_e%02d_minus(%02d_%02d) -f_%02d_%02d(e%02d) >= 0\n", KAPAZITÄT, kant, knote_i, knote_j, KAPAZITÄT, kant, knote_i, knote_j, KAPAZITÄT, kant, knote_i, knote_j, knote_i, knote_j, kant);
        fprintf(dateizeiger, "\n");
    }

    fprintf(dateizeiger, "\n\n");

    // Constriants 2 : \forall i,j\in N,i\neq j \pi_e(edge-of(a)) +p_e(i,j)-p_e(i,k)\geq0
    for(int kant=1; kant<=ANZAHL_KANTEN; kant++){
        for(int knote_i = 1; knote_i<=ANZAHL_KNOTEN; knote_i++)  { //knote_i = i
            int kant_h = 1; // kant_h = h
            for(int knote_j = 1; knote_j<=ANZAHL_KNOTEN; knote_j++)  // knote_j = j
                for(int knote_k = 1; knote_k<=ANZAHL_KNOTEN; knote_k++)    // knote_k = k
                    if((knote_j != knote_k)&& (BOGEN[knote_j-1][knote_k-1]==RICHTIG)){
                        if((knote_i != knote_k) && (knote_i != knote_k)){
                            fprintf(dateizeiger, "pi_e%02d(h%02d) + p_e%02d(%02d_%02d) - p_e%02d(%02d_%02d) >= 0\n", kant, kant_h, kant, knote_i, knote_j, kant, knote_i, knote_k);
                            kant_h ++;
                        }else if(knote_i != knote_j){
                            fprintf(dateizeiger, "pi_e%02d(h%02d) + p_e%02d(%02d_%02d) >= 0\n", kant, kant_h, kant, knote_i, knote_j);
                            kant_h ++;
                        }else if(knote_i != knote_k){
                            fprintf(dateizeiger, "pi_e%02d(h%02d) - p_e%02d(%02d_%02d) >= 0\n", kant, kant_h, kant, knote_i, knote_k);
                            kant_h ++;
                        }
					}
        }
        fprintf(dateizeiger, "\n");
    }

    fprintf(dateizeiger, "\n\n");
    
    // Constraint 3 : \sum_{ij}(s_e^-(i,j)a_{ij}-s_e^+(i,j)b_{ij})\geq0
    for(int kant=1; kant<=ANZAHL_KANTEN; kant++){
        for(int knote_i = 1; knote_i<=ANZAHL_KNOTEN; knote_i++)  { //knote_i = i
            for(int knote_j = 1; knote_j<=ANZAHL_KNOTEN; knote_j++){
                if(knote_i < knote_j)
                    fprintf(dateizeiger, "%d s_e%02d_minus(%02d_%02d) - %d s_e%02d_plus(%02d_%02d)", knote_i, kant ,knote_i, knote_j, knote_j, kant ,knote_i, knote_j);// ?
                if(knote_i > knote_j)
                    fprintf(dateizeiger, "%d s_e%02d_minus(%02d_%02d) - %d s_e%02d_plus(%02d_%02d)", knote_j, kant ,knote_i, knote_j, knote_i, kant ,knote_i, knote_j);// ?
                if((!((knote_i == ANZAHL_KNOTEN) && (knote_j == (ANZAHL_KNOTEN - 1)))) && (knote_i != knote_j))
                    fprintf(dateizeiger, " + ");
                if((knote_i == ANZAHL_KNOTEN) && (knote_j == ANZAHL_KNOTEN))
                    fprintf(dateizeiger, " >= 0\n");
            }
        }
        fprintf(dateizeiger, "\n");
    }

    fprintf(dateizeiger, "\n\n");

    // Speichern Sie die Textdatei
    fprintf(dateizeiger,"End\n");
    fclose(dateizeiger);
    dateizeiger = (FILE*)NULL;
    
    return ERFOLG;
}