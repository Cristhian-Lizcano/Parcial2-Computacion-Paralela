/* montecarlo.c -- version paralela con OpenMP.
   Uso: ./montecarlo <numero de muestras> [hilos] [semilla] [static|dynamic] [bloque]
   Compilar: gcc -O2 -fopenmp montecarlo.c -o montecarlo -lm

   Se conserva la estructura del programa secuencial de referencia: dos
   coordenadas por muestra generadas con rand_r, prueba x*x + y*y <= 1 y un
   contador de aciertos. La version paralela reparte el ciclo con
   "omp parallel for" y combina los aciertos con reduction(+:dentro).

   Flujo aleatorio por hilo.  rand_r de glibc avanza su estado con el LCG
       s <- s * 1103515245 + 12345   (modulo 2^32)
   tres veces por llamada.  La muestra i consume las llamadas 2i y 2i+1, es
   decir, los pasos 6i ... 6i+5 de una unica secuencia global que arranca en
   la semilla asignada.  Cada hilo coloca su estado privado en el paso 6*i del
   primer indice que recibe mediante un salto algebraico (composicion binaria
   de la transformacion afin), y desde ahi llama al rand_r real.  Asi:
     - los flujos de los hilos son tramos disjuntos de la misma secuencia,
       separados por lo menos 2N/p llamadas (>= N/p valores);
     - el conjunto de puntos no depende de p ni de la planificacion, por lo
       que la estimacion es identica para cualquier numero de hilos y
       coincide con la del programa secuencial con la misma semilla.
   Al arrancar, el programa comprueba que el salto reproduce el estado que
   deja rand_r de la biblioteca; si no coincide, se detiene. */
#define _POSIX_C_SOURCE 200809L
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LCG_A 1103515245u
#define LCG_C 12345u
#define PASOS_POR_MUESTRA 6u          /* 2 llamadas a rand_r x 3 pasos */

/* Estado tras aplicar 'delta' pasos del LCG a 'estado' (aritmetica mod 2^32). */
static unsigned int saltar(unsigned int estado, unsigned long delta)
{
    unsigned int a = LCG_A, c = LCG_C;      /* un paso: s -> a*s + c      */
    unsigned int a_ac = 1u, c_ac = 0u;      /* acumulado: s -> a_ac*s + c_ac */
    while (delta > 0) {
        if (delta & 1u) {
            a_ac *= a;
            c_ac = c_ac * a + c;
        }
        c = (a + 1u) * c;                   /* doble paso: a*(a*s+c)+c     */
        a *= a;
        delta >>= 1;
    }
    return a_ac * estado + c_ac;
}

/* Verifica que saltar(semilla, 6*i) coincide con el estado que deja rand_r
   tras consumir i muestras.  Prueba 1000 muestras consecutivas. */
static int verificar_salto(unsigned int semilla)
{
    unsigned int estado = semilla;
    for (long i = 0; i < 1000; i++) {
        if (saltar(semilla, PASOS_POR_MUESTRA * (unsigned long)i) != estado)
            return 0;
        (void)rand_r(&estado);
        (void)rand_r(&estado);
    }
    return 1;
}

int main(int argc, char *argv[])
{
    long N = (argc > 1) ? atol(argv[1]) : 100000000L;
    int p = (argc > 2) ? atoi(argv[2]) : 0;          /* 0: usar OMP_NUM_THREADS */
    unsigned int semilla = (argc > 3) ? (unsigned int)strtoul(argv[3], NULL, 10)
                                      : 2191050u;      /* semilla asignada */
    const char *politica = (argc > 4) ? argv[4] : "static";
    int bloque = (argc > 5) ? atoi(argv[5]) : 0;

    if (N < 1 || p < 0 || bloque < 0 ||
        (strcmp(politica, "static") != 0 && strcmp(politica, "dynamic") != 0)) {
        fprintf(stderr, "Uso: %s <N> [hilos] [semilla] [static|dynamic] [bloque]\n", argv[0]);
        return 1;
    }
    if (!verificar_salto(semilla)) {
        fprintf(stderr, "El salto de estado no coincide con rand_r de esta biblioteca\n");
        return 1;
    }
    if (p > 0)
        omp_set_num_threads(p);
    omp_set_dynamic(0);
    omp_set_schedule(strcmp(politica, "static") == 0 ? omp_sched_static
                                                     : omp_sched_dynamic, bloque);

    long dentro = 0;
    unsigned int estado = semilla;      /* copia privada por hilo (firstprivate) */
    long siguiente = -1;                /* proximo indice contiguo del hilo      */
    int hilos = omp_get_max_threads();  /* tamano del equipo que se creara      */

    double inicio = omp_get_wtime();
    #pragma omp parallel for default(none) shared(N, semilla) \
        firstprivate(estado, siguiente) reduction(+:dentro) schedule(runtime)
    for (long i = 0; i < N; i++) {
        if (i != siguiente)             /* comienzo de un tramo: posicionar */
            estado = saltar(semilla, PASOS_POR_MUESTRA * (unsigned long)i);
        double x = rand_r(&estado) / (double)RAND_MAX;
        double y = rand_r(&estado) / (double)RAND_MAX;
        if (x * x + y * y <= 1.0)
            dentro++;
        siguiente = i + 1;
    }
    double tiempo = omp_get_wtime() - inicio;

    printf("Estimacion de pi: %.6f\n", 4.0 * dentro / (double)N);
    printf("Aciertos: %ld de %ld\n", dentro, N);
    printf("Hilos: %d  Planificacion: %s,%d  Semilla: %u\n", hilos, politica, bloque, semilla);
    printf("Tiempo: %.6f s\n", tiempo);
    return 0;
}
