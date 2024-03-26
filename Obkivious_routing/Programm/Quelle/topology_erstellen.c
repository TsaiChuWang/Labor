#define ALLE_GLEICHE_KAPAZITÄT

#define DATEI_NAME "topologyZuStreit"

#include "../Enthalten/Aufbau.h"

#include <stdio.h>
#include <stdlib.h>

#define SYMMETRIC
#define DEBUG_DRUCKEN

int** erstellenTopology(int anzahl_knoten);
void fehlererkennuen(int anzahl_kanten, int anzahl_knoten, int** topology);

int main()
{
    // Öffnen Sie die Textdatei
	FILE *dateizeiger;
	dateizeiger = fopen("../Datei/"DATEI_NAME".txt","w+");
	
    int code;
    printf("case : ");
    scanf("%d", &code);
    fprintf(dateizeiger, "case %d:\n", code);

    char* datei_name[MAX_NAME_LÄNGE];
    printf("DATEI_NAME : ");
    scanf("%s", &datei_name);
    fprintf(dateizeiger, "\tstreit.DATEI_NAME = \"%s\";\n\n", datei_name);

    int anzahl_kanten, anzahl_knoten;
    printf("ANZAHL_KANTEN : ");
    scanf("%d", &anzahl_kanten);
    printf("ANZAHL_KNOTEN : ");
    scanf("%d", &anzahl_knoten);

    fprintf(dateizeiger, "\tstreit.ANZAHL_KANTEN = %d;\n", anzahl_kanten);
    fprintf(dateizeiger, "\tstreit.ANZAHL_KNOTEN = %d;\n\n", anzahl_knoten);

    int kapazität;
    printf("kapazität : ");
    scanf("%d", &kapazität);
    fprintf(dateizeiger, "\tstreit.GLEICHE_KAPAZITÄT = %d;\n\n", kapazität);
    
    int** topology = erstellenTopology(anzahl_knoten);
    fprintf(dateizeiger, "\tint topology_%d[%d][%d] =\n", code, anzahl_knoten, anzahl_knoten);
    for(int index = 0;index<anzahl_knoten;index++)
        for(int jndex = 0;jndex<anzahl_knoten;jndex++)
            if(jndex == 0){
                if(index == 0)
                    fprintf(dateizeiger, "\t\t{{%d,", topology[index][jndex]);
                else fprintf(dateizeiger, "\t\t {%d,", topology[index][jndex]);
            }else if(jndex == anzahl_knoten-1){
                if(index == anzahl_knoten-1)
                    fprintf(dateizeiger, "%d}};\n\n", topology[index][jndex]);
                else fprintf(dateizeiger, "%d},\n", topology[index][jndex]);
            }else fprintf(dateizeiger, "%d,", topology[index][jndex]);
    
    fprintf(dateizeiger, "\tstreit.BOGEN = bereichkopieren(streit.ANZAHL_KNOTEN, topology_%d);\n", code);
    fprintf(dateizeiger, "\tstreit.LISTE = bereichkopieren(streit.ANZAHL_KNOTEN, topology_%d);\n\n", code);
    fprintf(dateizeiger, "\tbreak;\n");

    fprintf(dateizeiger, "\n-------------------------\n");
    fprintf(dateizeiger, "if(strcmp(name, \"%s\") == ERFOLG)\n", datei_name);
    fprintf(dateizeiger, "\treturn %d;\n", code);
    
    fehlererkennuen(anzahl_kanten, anzahl_knoten, topology);

    fclose(dateizeiger);
}

int** erstellenTopology(int anzahl_knoten){
    int** topology = (int**)calloc(anzahl_knoten, sizeof(int*));
    for(int i =0;i<anzahl_knoten;i++)
        *(topology+i) = (int*)calloc(anzahl_knoten, sizeof(int));
    
    int start = 0;
    printf("Gehen auf : ");
    scanf("%d", &start);
    if(start != ERFOLG)
        start = 1;

#ifdef SYMMETRIC
    for(int index =0;index<anzahl_knoten;index++){
        if(start != ERFOLG)
            printf("Connected edges of node %d : ", index+1);
        else printf("Connected edges of node %d : ", index);

        do{
            int jndex = 0;
            scanf("%d", &jndex);
            if(start != ERFOLG){
                if(jndex > anzahl_knoten) { index--; continue; }
                topology[index][jndex-1] = RICHTIG;
                topology[jndex-1][index] = RICHTIG;
            }else{
                if(jndex > anzahl_knoten-1) { index--; continue; }
                topology[index][jndex] = RICHTIG;
                topology[jndex][index] = RICHTIG;
            } 
        }while (getchar()!='\n');
    }
#else
    for(int index =0;index<anzahl_knoten;index++){
        if(start != ERFOLG)
            printf("Connected edges of node %d : ", index+1);
        else printf("Connected edges of node %d : ", index);

        do{
            int jndex = 0;
            scanf("%d", &jndex);
            if(start != ERFOLG)
                topology[index][jndex-1] = RICHTIG;
            else
                topology[index][jndex] = RICHTIG;
        }while (getchar()!='\n');
    }
#endif

#ifdef DEBUG_DRUCKEN
    for(int index=0;index<anzahl_knoten;index++){
        for(int jndex=0;jndex<anzahl_knoten;jndex++)
            printf(" %d ", topology[index][jndex]);
        printf("\n");
    }
#endif

    return topology;
}

void fehlererkennuen(int anzahl_kanten, int anzahl_knoten, int** topology){
    int scahlter = 0;
    for(int index=0;index<anzahl_knoten;index++)
        for(int jndex=0;jndex<anzahl_knoten;jndex++)
            scahlter += *(*(topology+index)+jndex);
    printf("anzahl_kanten = %d, scahlter = %d\n", anzahl_kanten, scahlter);
    if(scahlter!=anzahl_kanten)
        printf("ERROR : INVALID TOPOLOGY!\n");
    else printf("VALID TOPOLOGY!\n");
}
