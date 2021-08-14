#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;
using namespace boost;
using namespace boost::algorithm;

// CPP code for Dynamic Programming based
// solution for 0-1 Knapsack problem

// A utility function that returns maximum of two integers
int max(int a, int b) { return (a > b) ? a : b; }
int sumw;
int X1050;
int Baellie;

stringstream sstream;
ofstream MyFile("..//output.txt");

typedef struct {
    string type;
    string name;
    int weight;
    int thrust;
} engine;

typedef struct {
    int total;
    int thrust;
    int steering;
} outfitSpace;

typedef struct {
    outfitSpace proposed;
    outfitSpace actual;
    vector<engine> steering;
    vector<engine> thrusters;
    string signature;
    int thrust;
    int steer;
    int total;
} record;

const vector<engine> thrusters = {
    {"Human plasma", "Chipmunk Plasma Thruster", 20, 34560},
    {"Human plasma", "Greyhound Plasma Thruster", 34, 66240},
    {"Human plasma", "Impala Plasma Thruster", 58, 127440},
    {"Human plasma", "Orca Plasma Thruster", 98, 244440},
    {"Human plasma", "Tyrant Plasma Thruster", 167, 469800},
    {"Human ion", "X1050 Ion Engines", 20, 14400},
    {"Human ion", "X1700 Ion Thruster", 16, 21600},
    {"Human ion", "X2700 Ion Thruster", 27, 41400},
    {"Human ion", "X3700 Ion Thruster", 46, 79560},
    {"Human ion", "X4700 Ion Thruster", 79, 153000},
    {"Human ion", "X5700 Ion Thruster", 134, 293400},
    {"Human atomic", "A120 Atomic Thruster", 22, 55400},
    {"Human atomic", "A250 Atomic Thruster", 34, 98280},
    {"Human atomic", "A370 Atomic Thruster", 53, 171360},
    {"Human atomic", "A520 Atomic Thruster", 82, 294840},
    {"Human atomic", "A860 Atomic Thruster", 127, 502920},
    {"Hai atomic", "Baellie Atomic Engines", 24, 36360},
    {"Hai atomic", "Basrem Atomic Thruster", 18, 47520},
    {"Hai atomic", "Benga Atomic Thruster", 28, 84960},
    {"Hai atomic", "Biroo Atomic Thruster", 44, 149400},
    {"Hai atomic", "Bondir Atomic Thruster", 63, 237960},
    {"Hai atomic", "Bufaer Atomic Thruster", 104, 432360},
    {"Wanderer radiant", "Type 1 Radiant Thruster", 12, 23760},
    {"Wanderer radiant", "Type 2 Radiant Thruster", 27, 63360},
    {"Wanderer radiant", "Type 3 Radiant Thruster", 42, 113400},
    {"Wanderer radiant", "Type 4 Radiant Thruster", 65, 198720},
    {"Korath", "Thruster (Asteroid Class)", 14, 40320},
    {"Korath", "Thruster (Comet Class)", 24, 78480},
    {"Korath", "Thruster (Lunar Class)", 40, 148320},
    {"Korath", "Thruster (Planetary Class)", 69, 288000},
    {"Korath", "Thruster (Stellar Class)", 118, 552240},
    {"Coalition", "Small Thrust Module", 9, 23760},
    {"Coalition", "Large Thrust Module", 32, 94320},
    {"Pug", "Pug Akfar Thruster", 43, 100800},
    {"Pug", "Pug Cormet Thruster", 60, 158400},
    {"Pug", "Pug Lohmar Thruster", 84, 237600},
    {"Quarg/Drak graviton", "Medium Gravitron Thruster", 70, 288000},
    {"Remnant", "Crucible Class Thruster", 20, 64800},
    {"Remnant", "Forge Class Thruster", 39, 133200},
    {"Remnant", "Smelter Class Thruster", 76, 276480},

};

const vector<engine> steering = {
    {"Human plasma", "Chipmunk Plasma Steering", 15, 15360},
    {"Human plasma", "Greyhound Plasma Steering", 26, 29520},
    {"Human plasma", "Impala Plasma Steering", 43, 56640},
    {"Human plasma", "Orca Plasma Steering", 74, 108720},
    {"Human plasma", "Tyrant Plasma Steering", 125, 208740},
    {"Human ion", "X1050 Ion Engines", 20, 6600},
    {"Human ion", "X1200 Ion Steering", 12, 9600},
    {"Human ion", "X2200 Ion Steering", 20, 18420},
    {"Human ion", "X3200 Ion Steering", 35, 35400},
    {"Human ion", "X4200 Ion Steering", 59, 67900},
    {"Human ion", "X5200 Ion Steering", 100, 130440},
    {"Human atomic", "A125 Atomic Steering", 16, 23520},
    {"Human atomic", "A255 Atomic Steering", 25, 41220},
    {"Human atomic", "A375 Atomic Steering", 38, 71520},
    {"Human atomic", "A525 Atomic Steering", 60, 123000},
    {"Human atomic", "A865 Atomic Steering", 92, 210540},
    {"Hai atomic", "Baellie Atomic Engines", 24, 15000},
    {"Hai atomic", "Basrem Atomic Steering", 12, 18540},
    {"Hai atomic", "Benga Atomic Steering", 20, 34620},
    {"Hai atomic", "Biroo Atomic Steering", 32, 63240},
    {"Hai atomic", "Bondir Atomic Steering", 49, 105480},
    {"Hai atomic", "Bufaer Atomic Steering", 76, 182580},
    {"Wanderer radiant", "Type 1 Radiant Steering", 9, 10368},
    {"Wanderer radiant", "Type 2 Radiant Steering", 20, 27240},
    {"Wanderer radiant", "Type 3 Radiant Steering", 30, 47160},
    {"Wanderer radiant", "Type 4 Radiant Steering", 47, 83754},
    {"Korath", "Steering (Asteroid Class)", 10, 16800},
    {"Korath", "Steering (Comet Class)", 18, 34128},
    {"Korath", "Steering (Lunar Class)", 30, 63360},
    {"Korath", "Steering (Planetary Class)", 52, 124176},
    {"Korath", "Steering (Stellar Class)", 89, 240300},
    {"Coalition", "Small Steering Miodule", 7, 10728},
    {"Coalition", "Large Steering Module", 25, 42714},
    {"Pug", "Pug Akfar Steering", 33, 45000},
    {"Pug", "Pug Cormet Steering", 46, 67800},
    {"Pug", "Pug Lohmar Steering", 64, 102000},
    {"Quarg/Drak graviton", "Medium Gravitron Steering", 50, 96000},
    {"Remnant", "Crucible Class Thruster", 14, 26880},
    {"Remnant", "Forge Class Thruster", 28, 57120},
    {"Remnant", "Smelter Class Thruster", 55, 118800},

};
vector<engine> findMatch(vector<engine> engines, vector<string> words) {
    vector<engine> match;
    for (auto engine : engines) {
        for (auto word : words) {
            if (icontains(engine.type, word)) {
                bool inside = false;
                for (auto matchedEngine : match) {
                    if (iequals(engine.name, matchedEngine.name)) {
                        inside = true;
                    }
                }
                if (inside == false) {
                    match.push_back(engine);
                }
            }
        }
    }
    std::cout << endl;
    return match;
}

// Prints the items which are put in a knapsack of capacity W
void printknapSack(int W, vector<engine> engines, const char *word,
                   string *signature, stringstream *local, record *record,
                   vector<engine> *engine) {
    int n = engines.size();
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
            else if (engines[i - 1].weight <= w)
                K[i][w] = max(engines[i - 1].thrust +
                                  K[i - 1][w - engines[i - 1].weight],
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
            temp << "\t" << engines[i - 1].weight << "\t" << engines[i - 1].name
                 << "\n";
            // *signature += ;
            record->signature += temp.str();
            engine->push_back(engines[i - 1]);
            //*local << "\t" << engine[i - 1].weight << "\t" << engine[i -
            // 1].name  << "\n";
            sumw += engines[i - 1].weight;
            if (equals(engines[i - 1].name, "X1050 Ion Engines")) {
                X1050++;
            }
            if (equals(engines[i - 1].name, "Baellie Atomic Engines")) {
                Baellie++;
            }
            // Since this weight is included its
            // value is deducted
            res -= engines[i - 1].thrust;
            w -= engines[i - 1].weight;
        }
    }
    //*local << "Outfit: " << sumw << "\n";
    //*local << word << "\t" << res1 << "\n";

    for (i = 0; i < r; i++)
        free(K[i]);
    free(K);
}

// Driver code
int main(int argc, char *argv[]) {
    int W;
    vector<string> match;
    if (argc <= 2) {
        W = 88;
        match = {"Human", "hai"};
    } else {
        W = atoi(argv[1]);
        for (int i = 2; i < argc; i++) {
            match.push_back(argv[i]);
        }
    }

    string oldSig;
    string newSig;

    vector<engine> thrustersFiltered = findMatch(thrusters, match);
    vector<engine> steeringFiltered = findMatch(steering, match);
    vector<record> records;

    for (int i = 0; i <= W; i++) {
        record temp;
        records.push_back(temp);

        records[i].proposed.thrust = i;
        records[i].proposed.steering = W - i;
        records[i].proposed.total = W;

        stringstream local;

        local << "---------------------------------------------\n";
        local << "Total:\t" << W << "\t";
        local << "Thrust:\t" << i << "\t";
        local << "Steer:\t" << W - i << "\n\n";

        printknapSack(i, thrustersFiltered, "Thrust:  ", &newSig, &local,
                      &(records[i]), &(records[i].thrusters));
        records[i].actual.thrust = 0;
        for (auto engine : records[i].thrusters) {
            local << "\t" << engine.weight << "\t" << engine.name << "\n";
            records[i].actual.thrust += engine.thrust;
            records[i].actual.total += engine.thrust;
        }
        local << "Outfit: " << sumw << "\n";
        local << "Thrust:  "
              << "\t" << records[i].actual.thrust << "\n";
        // cout << newSig;
        local << "\n";

        printknapSack(W - i, steeringFiltered, "Steering:", &newSig, &local,
                      &(records[i]), &(records[i].steering));
        records[i].actual.steering = 0;
        for (auto engine : records[i].steering) {
            local << "\t" << engine.weight << "\t" << engine.name << "\n";
            records[i].actual.steering += engine.thrust;
            records[i].actual.total += engine.thrust;
        }
        local << "Outfit: " << sumw << "\n";
        local << "Steering:"
              << "\t" << records[i].actual.steering << "\n";
        local << "---------------------------------------------\n";
        if (i == 0 ||
            equals(records[i - 1].signature, records[i].signature) == false)
            sstream << local.str();
    }
    // cout << sstream.str();
    MyFile << sstream.str();
    return 0;
}
