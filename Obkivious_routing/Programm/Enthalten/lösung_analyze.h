#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "./Aufbau.h"
#include "./Streit.h"

#define SCHLÜSSEL_GAMMA "  <variable name=\"r\""
#define SCHLÜSSEL_WERT "value=\""
#define SCHLÜSSEL_VERKEHR "  <variable name=\"f_%02d_%02d(e%02d)\""

#define LÖSUNG_ANALYZE

#ifdef LÖSUNG_ANALYZE

int istabgestimmt(char* prepared_string, char* key_string){
	if(strlen(prepared_string)<strlen(key_string))
		return FEHLGESCHLAGEN;
	for(int index=0;index<strlen(key_string);index++)
		if((int)(*(prepared_string+index)==*(key_string+index)) != RICHTIG)
			return FEHLGESCHLAGEN;
	return RICHTIG;
}

double erhaltenWert(char* prepared_string, char* key_string){
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

double*** erhaltenVerkehr(struct Streit streit){
    // Globale Paraneter erstellen
	char* DATEI_NAME = streit.DATEI_NAME;
	int ANZAHL_KANTEN = streit.ANZAHL_KANTEN;
	int ANZAHL_KNOTEN = streit.ANZAHL_KNOTEN;

#ifdef ALLE_GLEICHE_KAPAZITÄT
	int KAPAZITÄT = streit.GLEICHE_KAPAZITÄT;
#endif

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
		// Verkehr finden
		for(int kant = 0;kant<ANZAHL_KANTEN;kant++)
			for(int knote_i= 0 ;knote_i<ANZAHL_KNOTEN;knote_i++)
				for(int knote_j= 0 ;knote_j<ANZAHL_KNOTEN;knote_j++){
					char verkehr_linie[MAX_NAME_LÄNGE];
					sprintf(verkehr_linie, SCHLÜSSEL_VERKEHR, knote_i, knote_j, kant);

					if(istabgestimmt(linie, verkehr_linie) == RICHTIG){
						double verkehr = erhaltenWert(linie, SCHLÜSSEL_WERT);
#ifdef DEBUG_DRUCKEN
						printf("f_%02d_%02d(e%02d) = %lf\n", knote_i, knote_j, kant, verkehr);
#endif
						verkehrsarray[kant][knote_i][knote_j] = verkehr;
					}
				}
    }

    fclose(dateizeiger);
    if (linie)
        free(linie);

    return verkehrsarray;
}

double erhaltenGamma(struct Streit streit){
    double gamma = (double)-1;
    char* DATEI_NAME = streit.DATEI_NAME;
	int ANZAHL_KANTEN = streit.ANZAHL_KANTEN;
	int ANZAHL_KNOTEN = streit.ANZAHL_KNOTEN;

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
    
    while ((read = getline(&linie, &länge, dateizeiger)) != FEHLGESCHLAGEN) {
		// Gamma finden
		if(istabgestimmt(linie, SCHLÜSSEL_GAMMA) == RICHTIG){
#ifdef DEBUG_DRUCKEN
			printf("gamma linie = %s\n", linie);
#endif
			gamma = erhaltenWert(linie, SCHLÜSSEL_WERT);
			if(gamma<ERFOLG){
				printf("ERROR\n");
				exit(EXIT_FAILURE);
			}
#ifdef DEBUG_DRUCKEN
			printf("streit.gamma = %lf;\n\n", gamma);
#endif
		}
    }

    fclose(dateizeiger);
    if (linie)
        free(linie);
    return gamma;
}

void druckenEinzelKant(double*** verkehrsarray, struct Streit streit, int kant_index){
    int ANZAHL_KANTEN = streit.ANZAHL_KANTEN;
	int ANZAHL_KNOTEN = streit.ANZAHL_KNOTEN;

    if(kant_index >= ANZAHL_KANTEN){
        printf("ERROR : KANT INDEX AUSSERHALB DER GRENZEN\n");
        return;
    }

    printf("\nDatenverkehr am Rand %2d : \n");
    for(int knote_i = 0;knote_i<ANZAHL_KNOTEN;knote_i++){
        for(int knote_j = 0;knote_j<ANZAHL_KNOTEN;knote_j++)
            printf(" %lf ", verkehrsarray[kant_index][knote_i][knote_j]);
        printf("\n");
    }
}

void druckenKanten(double*** verkehrsarray, struct Streit streit){
    for(int kant = 0;kant<streit.ANZAHL_KANTEN;kant++)
        druckenEinzelKant(verkehrsarray, streit, kant);
}

#endif

