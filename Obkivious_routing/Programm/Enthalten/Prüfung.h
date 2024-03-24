#define DATEI_NAME "ausführbar"

#define ANZAHL_KANTEN 12    // Number of edges
#define ANZAHL_KNOTEN 6     // Number of nodes

#ifdef ALLE_GLEICHE_KAPAZITÄT// Each link has same capacity 
    #define KAPAZITÄT 77
#endif

#define PRÜFUNG
#ifdef PRÜFUNG

int BOGEN[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,1,1,0,0,0},
	 {1,0,0,1,0,0},
	 {1,0,0,0,1,0},
	 {0,1,0,0,0,1},
	 {0,0,1,0,0,1},
	 {0,0,0,1,1,0}};

int LISTE[ANZAHL_KNOTEN][ANZAHL_KNOTEN]=
    {{0,1,1,0,0,0},	
     {1,0,0,1,0,0},
	 {1,0,0,0,1,0},
	 {0,1,0,0,0,1},
	 {0,0,1,0,0,1},
	 {0,0,0,1,1,0}};

#endif