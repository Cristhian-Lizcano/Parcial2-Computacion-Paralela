/* montecarlo_secuencial.c -- version secuencial de referencia (enunciado).
   Uso: ./montecarlo_secuencial <numero de muestras> [semilla]
   Compilar: gcc -O2 -fopenmp montecarlo_secuencial.c -o montecarlo_secuencial -lm

   Respecto al programa del enunciado solo se agregan: la semilla asignada
   como valor por defecto (opcionalmente por argumento), el cronometro con
   omp_get_wtime() para registrar T(1), y la impresion de los aciertos para
   contrastar con la version paralela. */
#define _POSIX_C_SOURCE 200809L
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    long N = (argc > 1) ? atol(argv[1]) : 100000000L;
    unsigned int semilla = (argc > 2) ? (unsigned int)strtoul(argv[2], NULL, 10)
                                      : 2191050u;      /* semilla asignada */
    unsigned int estado = semilla;      /* estado del generador */
    long dentro = 0;

    if (N < 1) {
        fprintf(stderr, "Uso: %s <N> [semilla]\n", argv[0]);
        return 1;
    }

    double inicio = omp_get_wtime();
    for (long i = 0; i < N; i++) {
        double x = rand_r(&estado) / (double)RAND_MAX;
        double y = rand_r(&estado) / (double)RAND_MAX;
        if (x * x + y * y <= 1.0)
            dentro++;
    }
    double tiempo = omp_get_wtime() - inicio;

    printf("Estimacion de pi: %.6f\n", 4.0 * dentro / (double)N);
    printf("Aciertos: %ld de %ld\n", dentro, N);
    printf("Hilos: 1  Planificacion: secuencial  Semilla: %u\n", semilla);
    printf("Tiempo: %.6f s\n", tiempo);
    return 0;
}
