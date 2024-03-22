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
            fprintf(dateizeiger, "%d pi_e%02d(h%02d)", (int)KAPAZITÄT, kant_eins, kant_zwei);
            if(kant_zwei == ANZAHL_KANTEN)
                fprintf(dateizeiger, " <= r\n");
            else fprintf(dateizeiger, " + ");
        }
    }

    // for(int umrande)

    // Speichern Sie die Textdatei
    fprintf(dateizeiger,"End\n");
    fclose(dateizeiger);
    dateizeiger = (FILE*)NULL;
    
    return ERFOLG;
}