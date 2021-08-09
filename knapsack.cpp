#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>

using namespace std;
// CPP code for Dynamic Programming based
// solution for 0-1 Knapsack problem

// A utility function that returns maximum of two integers
int max(int a, int b) { return (a > b) ? a : b; }
int sumw;
int X1050;
int Baellie;
// Prints the items which are put in a knapsack of capacity W
void printknapSack(int W, int wt[], int val[], int n, const char *names[],
                   const char *word) {
    X1050 = 0;
    Baellie = 0;
    sumw = 0;
    int i, w;
    int r = n + 1, c = W + 1;
    int **K = (int **)malloc(r * sizeof(int *));
    for (i = 0; i < r; i++)
        K[i] = (int *)malloc(c * sizeof(int));

    // Build table K[][] in bottom up manner
    for (i = 0; i <= n; i++) {
        for (w = 0; w <= W; w++) {
            if (i == 0 || w == 0)
                K[i][w] = 0;
            else if (wt[i - 1] <= w)
                K[i][w] =
                    max(val[i - 1] + K[i - 1][w - wt[i - 1]], K[i - 1][w]);
            else
                K[i][w] = K[i - 1][w];
        }
    }

    // stores the result of Knapsack
    int res = K[n][W];
    int res1 = res;
    // cout << "Thrust:"<< res << "\n";

    w = W;
    for (i = n; i > 0 && res > 0; i--) {

        // either the result comes from the top
        // (K[i-1][w]) or from (val[i-1] + K[i-1]
        // [w-wt[i-1]]) as in Knapsack table. If
        // it comes from the latter one/ it means
        // the item is included.
        if (res == K[i - 1][w])
            continue;
        else {

            // This item is included.
            cout << "\t" << wt[i - 1] << "\t" << names[i - 1] << "\n";
            sumw = sumw + wt[i - 1];
            if (strcmp(names[i - 1], "X1050 Ion Engines") == 0)
                X1050++;
            if (strcmp(names[i - 1], "Baellie Atomic Engines") == 0)
                Baellie++;

            // Since this weight is included its
            // value is deducted
            res = res - val[i - 1];
            w = w - wt[i - 1];
        }
    }
    cout << "Outfit: " << sumw << "\n";
    cout << word << "\t" << res1 << "\n";
}

// Driver code
int main(int argc, char *argv[]) {
    freopen("output.txt", "w", stdout);
    if (argc != 2)
        return 1;
    int thrust[] = {34560,  66240,  127440, 244440, 469800, 21600,  41400,
                    79560,  153000, 293400, 55400,  98280,  171360, 294840,
                    502920, 47520,  84960,  149400, 237960, 432360, 23760,
                    63360,  113400, 198720, 40320,  78480,  148320, 288000,
                    552240, 23760,  94320,  100800, 158400, 237600, 288000,
                    64800,  133200, 276480, 14400,  36360};
    int tWeight[] = {20,  34, 58, 98, 167, 16,  27, 46, 79, 134, 22, 34, 53, 82,
                     127, 18, 28, 44, 63,  104, 12, 27, 42, 65,  14, 24, 40, 69,
                     118, 9,  32, 43, 60,  84,  70, 20, 39, 76,  20, 24};
    char const *tNames[]{
        "Chipmunk Plasma Thruster",  "Greyhound Plasma Thruster",
        "Impala Plasma Thruster",    "Orca Plasma Thruster",
        "Tyrant Plasma Thruster",    "X1700 Ion Thruster",
        "X2700 Ion Thruster",        "X3700 Ion Thruster",
        "X4700 Ion Thruster",        "X5700 Ion Thruster",
        "A120 Atomic Thruster",      "A250 Atomic Thruster",
        "A370 Atomic Thruster",      "A520 Atomic Thruster",
        "A860 Atomic Thruster",      "Basrem Atomic Thruster",
        "Benga Atomic Thruster",     "Biroo Atomic Thruster",
        "Bondir Atomic Thruster",    "Bufaer Atomic Thruster",
        "Type 1 Radiant Thruster",   "Type 2 Radiant Thruster",
        "Type 3 Radiant Thruster",   "Type 4 Radiant Thruster",
        "Thruster (Asteroid Class)", "Thruster (Comet Class)",
        "Thruster (Lunar Class)",    "Thruster (Planetary Class)",
        "Thruster (Stellar Class)",  "Small Thrust Module",
        "Large Thrust Module",       "Pug Akfar Thruster",
        "Pug Cormet Thruster",       "Pug Lohmar Thruster",
        "Medium Gravitron Thruster", "Crucible Class Thruster",
        "Forge Class Thruster",      "Smelter Class Thruster",
        "X1050 Ion Engines",         "Baellie Atomic Engines"};

    int steering[] = {15360,  29520, 56640,  108720, 208740, 9600,   18420,
                      35400,  67900, 130440, 23520,  41220,  71520,  123000,
                      210540, 18540, 34620,  63240,  105480, 182580, 10368,
                      27240,  47160, 83754,  16800,  34128,  63360,  124176,
                      240300, 10728, 42714,  45000,  67800,  102000, 96000,
                      26880,  57120, 118800, 6600,   15000};
    int sWeight[] = {15, 26, 43, 74, 125, 12, 20, 35, 59, 100, 16, 25, 38, 60,
                     92, 12, 20, 32, 49,  76, 9,  20, 30, 47,  10, 18, 30, 52,
                     89, 7,  25, 33, 46,  64, 50, 14, 28, 55,  20, 24};
    char const *sNames[]{
        "Chipmunk Plasma Steering",  "Greyhound Plasma Steering",
        "Impala Plasma Steering",    "Orca Plasma Steering",
        "Tyrant Plasma Steering",    "X1200 Ion Steering",
        "X2200 Ion Steering",        "X3200 Ion Steering",
        "X4200 Ion Steering",        "X5200 Ion Steering",
        "A125 Atomic Steering",      "A255 Atomic Steering",
        "A375 Atomic Steering",      "A525 Atomic Steering",
        "A865 Atomic Steering",      "Basrem Atomic Steering",
        "Benga Atomic Steering",     "Biroo Atomic Steering",
        "Bondir Atomic Steering",    "Bufaer Atomic Steering",
        "Type 1 Radiant Steering",   "Type 2 Radiant Steering",
        "Type 3 Radiant Steering",   "Type 4 Radiant Steering",
        "Steering (Asteroid Class)", "Steering (Comet Class)",
        "Steering (Lunar Class)",    "Steering (Planetary Class)",
        "Steering (Stellar Class)",  "Small Steering Miodule",
        "Large Steering Module",     "Pug Akfar Steering",
        "Pug Cormet Steering",       "Pug Lohmar Steering",
        "Medium Gravitron Steering", "Crucible Class Thruster",
        "Forge Class Thruster",      "Smelter Class Thruster",
        "X1050 Ion Engines",         "Baellie Atomic Engines"};
    int W = atoi(argv[1]);
    for (int i = 0; i <= W; i++) {
        cout << "---------------------------------------------\n";
        cout << "Total:\t" << W << "\t";
        cout << "Thrust:\t" << i << "\t";
        cout << "Steer:\t" << W - i << "\n\n";

        int n = sizeof(thrust) / sizeof(thrust[0]);
        printknapSack(i, tWeight, thrust, n, tNames, "Thrust:");
        cout << "\n";
        n = sizeof(steering) / sizeof(steering[0]);
        printknapSack(W - i, sWeight, steering, n, sNames, "Steer:");
        cout << "---------------------------------------------\n";
    }
    return 0;
}
