#include <stdio.h>

#define DATEI_NAME "NSFNET"

#define ANZAHL_KANTEN 42    // Number of edges
#define ANZAHL_KNOTEN 14     // Number of nodes

#ifdef ALLE_GLEICHE_KAPAZITÄT// Each link has same capacity 
    #define KAPAZITÄT 150
#endif

#define NSFNET
#ifdef NSFNET

int BOGEN[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,0,1,0,0,0,0,0,1,0,0,0,0,1},
	 {0,0,1,0,0,0,0,0,1,0,0,0,0,1},
	 {1,1,0,0,1,0,0,0,0,0,0,0,0,0},
	 {0,0,0,0,1,0,0,0,0,0,0,0,0,1},
	 {0,0,1,1,0,1,0,0,0,0,0,0,1,0},

	 {0,0,0,0,1,0,1,1,0,0,0,0,0,0},
	 {0,0,0,0,0,1,0,1,0,0,0,1,0,0},
	 {0,0,0,0,0,1,1,0,0,1,0,0,0,0},
	 {1,1,0,0,0,0,0,0,0,0,0,1,0,0},
	 {0,0,0,0,0,0,0,1,0,0,1,0,0,1},
	 
	 {0,0,0,0,0,0,0,0,0,1,0,0,1,0},
	 {0,0,0,0,0,0,1,0,1,0,0,0,1,0},
	 {0,0,0,0,1,0,0,0,0,0,1,1,0,0},
	 {1,1,0,1,0,0,0,0,0,1,0,0,0,0}};

int LISTE[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,0,1,0,0,0,0,0,1,0,0,0,0,1},
	 {0,0,1,0,0,0,0,0,1,0,0,0,0,1},
	 {1,1,0,0,1,0,0,0,0,0,0,0,0,0},
	 {0,0,0,0,1,0,0,0,0,0,0,0,0,1},
	 {0,0,1,1,0,1,0,0,0,0,0,0,1,0},

	 {0,0,0,0,1,0,1,1,0,0,0,0,0,0},
	 {0,0,0,0,0,1,0,1,0,0,0,1,0,0},
	 {0,0,0,0,0,1,1,0,0,1,0,0,0,0},
	 {1,1,0,0,0,0,0,0,0,0,0,1,0,0},
	 {0,0,0,0,0,0,0,1,0,0,1,0,0,1},
	 
	 {0,0,0,0,0,0,0,0,0,1,0,0,1,0},
	 {0,0,0,0,0,0,1,0,1,0,0,0,1,0},
	 {0,0,0,0,1,0,0,0,0,0,1,1,0,0},
	 {1,1,0,1,0,0,0,0,0,1,0,0,0,0}};

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