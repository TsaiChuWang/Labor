#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../Enthalten/Aufbau.h"
#include "../Enthalten/Streit.h"

#define SCHLÜSSEL_GAMMA "  <variable name=\"r\""
#define SCHLÜSSEL_WERT "value=\""
#define SCHLÜSSEL_VERKEHR "  <variable name=\"f_%02d_%02d(e%02d)\""

#define ALLE_GLEICHE_KAPAZITÄT
// #define DEBUG_DRUCKEN

int isMatched(char* prepared_string, char* key_string);
double obtainValue(char* prepared_string, char* key_string);

int main(int argc, char *argv[])
{
	// Drucken Sie die Streiten und Fehlgeschlagen
	if(argc<2){
		printf("ERROR : MISSING ARGUMENTS!\n");
		return FEHLGESCHLAGEN;
	}

	printf("Topology : %s [%d]\n\n", argv[1], zuordnungCode(argv[1]));
	if(zuordnungCode(argv[1]) == FEHLGESCHLAGEN){
		printf("ERROR : INVALID ARGUMENTS!\n");
		return FEHLGESCHLAGEN;
	}

	// Globale Paraneter erstellen
	int schalter;
	struct Streit streit = nehmenStreit(zuordnungCode(argv[1]));
	
	char* DATEI_NAME = streit.DATEI_NAME;
	int ANZAHL_KANTEN = streit.ANZAHL_KANTEN;
	int ANZAHL_KNOTEN = streit.ANZAHL_KNOTEN;

#ifdef ALLE_GLEICHE_KAPAZITÄT
	int KAPAZITÄT = streit.GLEICHE_KAPAZITÄT;
#endif

	int** BOGEN= streit.BOGEN;
	int** LISTE = streit.LISTE;

	// Lösungsdatei lesen
    FILE * dateizeiger;
    char * linie = NULL;
    size_t länge = 0;
    ssize_t read;

	char datei_name[MAX_NAME_LÄNGE];
	sprintf(datei_name, "../Lösung/%s.sol", DATEI_NAME);

	dateizeiger = fopen(datei_name,"r");
    if (dateizeiger == NULL)
        exit(EXIT_FAILURE);

	// Verkehrsarray initialisieren
	double*** verkehrsarray = (double***)calloc(ANZAHL_KANTEN, sizeof(double**));
	for(int kant = 0;kant<ANZAHL_KANTEN;kant++){
		*(verkehrsarray+kant) = (double**)calloc(ANZAHL_KNOTEN, sizeof(double*));
		for(int knote_i= 0 ;knote_i<ANZAHL_KNOTEN;knote_i++)
			*(*(verkehrsarray+kant)+knote_i) = (double*)calloc(ANZAHL_KNOTEN, sizeof(double));
	}

    while ((read = getline(&linie, &länge, dateizeiger)) != FEHLGESCHLAGEN) {

		// Gamma finden
		if(isMatched(linie, SCHLÜSSEL_GAMMA) == RICHTIG){
#ifdef DEBUG_DRUCKEN
			printf("gamma linie = %s\n", linie);
#endif
			double gamma = obtainValue(linie, SCHLÜSSEL_WERT);
			if(gamma<ERFOLG){
				printf("ERROR\n");
				exit(EXIT_FAILURE);
			}
			printf("streit.gamma = %lf;\n\n", gamma);
		}
		
		// Verkehr finden
		for(int kant = 0;kant<ANZAHL_KANTEN;kant++){
			for(int knote_i= 0 ;knote_i<ANZAHL_KNOTEN;knote_i++){
				for(int knote_j= 0 ;knote_j<ANZAHL_KNOTEN;knote_j++){
					char verkehr_linie[MAX_NAME_LÄNGE];
					sprintf(verkehr_linie, SCHLÜSSEL_VERKEHR, knote_i, knote_j, kant);
					// printf("%s\n", verkehr);

					if(isMatched(linie, verkehr_linie) == RICHTIG){
						double verkehr = obtainValue(linie, SCHLÜSSEL_WERT);
#ifdef DEBUG_DRUCKEN
						printf("f_%02d_%02d(e%02d) = %lf\n", knote_i, knote_j, kant, verkehr);
#endif
						verkehrsarray[kant][knote_i][knote_j] = verkehr;
					}
				}
			}
		}
    }

    fclose(dateizeiger);
    if (linie)
        free(linie);
    exit(EXIT_SUCCESS);
}

int isMatched(char* prepared_string, char* key_string){
	if(strlen(prepared_string)<strlen(key_string))
		return FEHLGESCHLAGEN;
	for(int index=0;index<strlen(key_string);index++)
		if((int)(*(prepared_string+index)==*(key_string+index)) != RICHTIG)
			return FEHLGESCHLAGEN;
	return RICHTIG;
}

double obtainValue(char* prepared_string, char* key_string){
	// find the index of value(start)
	int start_index = FEHLGESCHLAGEN;
	for(int index=0;index<strlen(prepared_string)-strlen(key_string)+1;index++){
		start_index = index;
		for(int jndex=0;jndex<strlen(key_string);jndex++)
			if(*(prepared_string+index+jndex) != *(key_string+jndex)){
				start_index = FEHLGESCHLAGEN;
				break;
			}
		if(start_index > FEHLGESCHLAGEN){
#ifdef DEBUG_DRUCKEN
			printf("start index = %d\n", start_index);
#endif
			break;
		}
	}
	if(start_index == FEHLGESCHLAGEN)	//Error detection
		return (double)FEHLGESCHLAGEN;
	
	// find the index of value(end)
	int end_index = FEHLGESCHLAGEN;
	for(int index=start_index+strlen(key_string);index<strlen(prepared_string);index++)
		if(*(prepared_string+index) == '\"'){
			end_index = index;
			break;
		}
	if(end_index == FEHLGESCHLAGEN)
		return (double)FEHLGESCHLAGEN;
#ifdef DEBUG_DRUCKEN
	printf("%d\n", end_index);
#endif 

	// Cut the string
	char* substring = (char*)malloc(sizeof(char)*(end_index-start_index-strlen(key_string)));
	for(int index = 0;index<end_index-start_index-strlen(key_string);index++)
		*(substring+index) = *(prepared_string+start_index+strlen(key_string)+index);
#ifdef DEBUG_DRUCKEN
	printf("%s\n", substring);
#endif

	// Obtain gamma
	double gamma = strtod(substring, NULL);
#ifdef DEBUG_DRUCKEN
	printf("gamma = %lf\n", gamma);
#endif
	free(substring);

	return gamma;
}