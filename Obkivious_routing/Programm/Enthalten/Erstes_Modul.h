#include <stdio.h>

#define DATEI_NAME "erste_modul"

#define ANZAHL_KANTEN 20    // Number of edges
#define ANZAHL_KNOTEN 6     // Number of nodes

#ifdef ALLE_GLEICHE_KAPAZITÄT// Each link has same capacity 
    #define KAPAZITÄT 100
#endif

#define MAX_NAME_LÄNGE 50

#define ERSTES_MODUL
#ifdef ERSTES_MODUL

int BOGEN[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,1,1,0,0,0},
	 {1,0,1,1,1,0},
	 {1,1,0,1,1,0},
	 {0,1,1,0,1,1},
	 {0,1,1,1,0,1},
	 {0,0,0,1,1,0}};

int LISTE[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,1,1,0,0,0},
	 {1,0,1,1,1,0},
	 {1,1,0,1,1,0},
	 {0,1,1,0,1,1},
	 {0,1,1,1,0,1},
	 {0,0,0,1,1,0}};

void druckinformationstopologie(){
	printf("edges : %3d nodes : %3d\n", ANZAHL_KANTEN, ANZAHL_KNOTEN);
	#ifdef ALLE_GLEICHE_KAPAZITÄT
		printf("capacity :%5d\n", KAPAZITÄT);
	#endif
	for(int knote_i=0;knote_i<ANZAHL_KNOTEN;knote_i++){
		for(int knote_j=0;knote_j<ANZAHL_KNOTEN;knote_j++)
			printf(" %d ", LISTE[knote_i][knote_j]);
		printf("\n");
	}
}

#endif