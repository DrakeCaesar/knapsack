#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;
// CPP code for Dynamic Programming based
// solution for 0-1 Knapsack problem

// A utility function that returns maximum of two integers
int max(int a, int b) { return (a > b) ? a : b; }
int sumw;
int X1050;
int Baellie;

stringstream sstream;
ofstream MyFile("..//output.txt");

struct Engine {
    string name;
    int weight;
    int thrust;
};

vector<struct Engine> thrusters = {{"Chipmunk Plasma Thruster", 20, 34560},
                                   {"Greyhound Plasma Thruster", 34, 66240},
                                   {"Impala Plasma Thruster", 58, 127440},
                                   {"Orca Plasma Thruster", 98, 244440},
                                   {"Tyrant Plasma Thruster", 167, 469800},
                                   {"X1700 Ion Thruster", 16, 21600},
                                   {"X2700 Ion Thruster", 27, 41400},
                                   {"X3700 Ion Thruster", 46, 79560},
                                   {"X4700 Ion Thruster", 79, 153000},
                                   {"X5700 Ion Thruster", 134, 293400},
                                   {"A120 Atomic Thruster", 22, 55400},
                                   {"A250 Atomic Thruster", 34, 98280},
                                   {"A370 Atomic Thruster", 53, 171360},
                                   {"A520 Atomic Thruster", 82, 294840},
                                   {"A860 Atomic Thruster", 127, 502920},
                                   {"Basrem Atomic Thruster", 18, 47520},
                                   {"Benga Atomic Thruster", 28, 84960},
                                   {"Biroo Atomic Thruster", 44, 149400},
                                   {"Bondir Atomic Thruster", 63, 237960},
                                   {"Bufaer Atomic Thruster", 104, 432360},
                                   {"Type 1 Radiant Thruster", 12, 23760},
                                   {"Type 2 Radiant Thruster", 27, 63360},
                                   {"Type 3 Radiant Thruster", 42, 113400},
                                   {"Type 4 Radiant Thruster", 65, 198720},
                                   {"Thruster (Asteroid Class)", 14, 40320},
                                   {"Thruster (Comet Class)", 24, 78480},
                                   {"Thruster (Lunar Class)", 40, 148320},
                                   {"Thruster (Planetary Class)", 69, 288000},
                                   {"Thruster (Stellar Class)", 118, 552240},
                                   {"Small Thrust Module", 9, 23760},
                                   {"Large Thrust Module", 32, 94320},
                                   {"Pug Akfar Thruster", 43, 100800},
                                   {"Pug Cormet Thruster", 60, 158400},
                                   {"Pug Lohmar Thruster", 84, 237600},
                                   {"Medium Gravitron Thruster", 70, 288000},
                                   {"Crucible Class Thruster", 20, 64800},
                                   {"Forge Class Thruster", 39, 133200},
                                   {"Smelter Class Thruster", 76, 276480},
                                   {"X1050 Ion Engines", 20, 14400},
                                   {"Baellie Atomic Engines", 24, 36360}

};

vector<struct Engine> steerings = {
    {"Chipmunk Plasma Steering", 15, 15360},
    {"Greyhound Plasma Steering", 26, 29520},
    {"Impala Plasma Steering", 43, 56640},
    {"Orca Plasma Steering", 74, 108720},
    {"Tyrant Plasma Steering", 125, 208740},
    {"X1200 Ion Steering", 12, 9600},
    {"X2200 Ion Steering", 20, 18420},
    {"X3200 Ion Steering", 35, 35400},
    {"X4200 Ion Steering", 59, 67900},
    {"X5200 Ion Steering", 100, 130440},
    {"A125 Atomic Steering", 16, 23520},
    {"A255 Atomic Steering", 25, 41220},
    {"A375 Atomic Steering", 38, 71520},
    {"A525 Atomic Steering", 60, 123000},
    {"A865 Atomic Steering", 92, 210540},
    {"Basrem Atomic Steering", 12, 18540},
    {"Benga Atomic Steering", 20, 34620},
    {"Biroo Atomic Steering", 32, 63240},
    {"Bondir Atomic Steering", 49, 105480},
    {"Bufaer Atomic Steering", 76, 182580},
    {"Type 1 Radiant Steering", 9, 10368},
    {"Type 2 Radiant Steering", 20, 27240},
    {"Type 3 Radiant Steering", 30, 47160},
    {"Type 4 Radiant Steering", 47, 83754},
    {"Steering (Asteroid Class)", 10, 16800},
    {"Steering (Comet Class)", 18, 34128},
    {"Steering (Lunar Class)", 30, 63360},
    {"Steering (Planetary Class)", 52, 124176},
    {"Steering (Stellar Class)", 89, 240300},
    {"Small Steering Miodule", 7, 10728},
    {"Large Steering Module", 25, 42714},
    {"Pug Akfar Steering", 33, 45000},
    {"Pug Cormet Steering", 46, 67800},
    {"Pug Lohmar Steering", 64, 102000},
    {"Medium Gravitron Steering", 50, 96000},
    {"Crucible Class Thruster", 14, 26880},
    {"Forge Class Thruster", 28, 57120},
    {"Smelter Class Thruster", 55, 118800},
    {"X1050 Ion Engines", 20, 6600},
    {"Baellie Atomic Engines", 24, 15000},
};

// Prints the items which are put in a knapsack of capacity W
void printknapSack(int W, vector<struct Engine> engine, int n, const char *word,
                   string *signature, stringstream *local) {
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
            else if (engine[i - 1].weight <= w)
                K[i][w] = max(engine[i - 1].thrust +
                                  K[i - 1][w - engine[i - 1].weight],
                              K[i - 1][w]);
            else
                K[i][w] = K[i - 1][w];
        }
    }

    // stores the result of Knapsack
    int res = K[n][W];
    int res1 = res;
    // sstream << "Thrust:"<< res << "\n";

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
            stringstream temp;
            temp << "\t" << engine[i - 1].weight << "\t" << engine[i - 1].name
                 << "\n";
            *signature = *signature + temp.str();
            *local << "\t" << engine[i - 1].weight << "\t" << engine[i - 1].name
                   << "\n";
            sumw = sumw + engine[i - 1].weight;
            if (strcmp(engine[i - 1].name.c_str(), "X1050 Ion Engines") == 0)
                X1050++;
            if (strcmp(engine[i - 1].name.c_str(), "Baellie Atomic Engines") ==
                0)
                Baellie++;

            // Since this weight is included its
            // value is deducted
            res = res - engine[i - 1].thrust;
            w = w - engine[i - 1].weight;
        }
    }
    *local << "Outfit: " << sumw << "\n";
    *local << word << "\t" << res1 << "\n";
}

// Driver code
int main(int argc, char *argv[]) {
    int W;
    if (argc != 2) {
        W = 40;
    } else {
        W = atoi(argv[1]);
    }

    string oldSig;
    string newSig;

    for (int i = 0; i <= W; i++) {
        oldSig = "" + newSig;
        newSig = "";
        stringstream local;

        local << "---------------------------------------------\n";
        local << "Total:\t" << W << "\t";
        local << "Thrust:\t" << i << "\t";
        local << "Steer:\t" << W - i << "\n\n";

        int n = thrusters.size();
        printknapSack(i, thrusters, n, "Thrust:  ", &newSig, &local);
        cout << newSig;
        local << "\n";
        n = steerings.size();
        printknapSack(W - i, steerings, n, "Steering:", &newSig, &local);
        local << "---------------------------------------------\n";
        if (oldSig.compare(newSig) != 0)
            sstream << local.str();
    }
    // cout << sstream.str();
    MyFile << sstream.str();
    return 0;
}
