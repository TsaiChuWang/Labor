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
    for(int kant=1; kant<=ANZAHL_KANTEN; kant++){
        for(int knote_i = 1; knote_i<ANZAHL_KNOTEN; knote_i++)
            for(int knote_j = 1; knote_j<ANZAHL_KNOTEN; knote_j++)
                if(knote_i != knote_j)
                    fprintf(dateizeiger, "%d p_e%02d(%02d_%02d) + %d s_e%02d_plus(%02d_%02d) - %d s_e%02d_minus(%02d_%02d) -f_%02d_%02d(e%02d) >= 0\n", KAPAZITÄT, kant, knote_i, knote_j, KAPAZITÄT, kant, knote_i, knote_j, KAPAZITÄT, kant, knote_i, knote_j, knote_i, knote_j, kant);
        fprintf(dateizeiger, "\n");
    }


    // Speichern Sie die Textdatei
    fprintf(dateizeiger,"End\n");
    fclose(dateizeiger);
    dateizeiger = (FILE*)NULL;
    
    return ERFOLG;
}