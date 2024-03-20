#include "./enhthalten/Aufbau.h"
#include <stdio.h>
#include <stdlib.h>

int main(void){
    // printf("Prüfung\n");

    FILE *dateizeiger;
    dateizeiger=fopen("./Datei/ausführbar.lp","w+");
	fprintf(dateizeiger,"min r\n");
	fprintf(dateizeiger,"Subject to \n");
    fprintf(dateizeiger,"End\n");
    return ERFOLG;
}