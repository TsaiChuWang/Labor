
#include "../Enthalten/lösung_analyze.h"

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
	struct Streit streit = nehmenStreit(zuordnungCode(argv[1]));

	double*** verkehrsarray = erhaltenVerkehr(streit);
	double gamma = erhaltenGamma(streit);

#ifdef DEBUG_DRUCKEN
	printf("gamma = %lf\n", gamma);
	druckenKanten(verkehrsarray, streit);
#endif
   	return ERFOLG;
}