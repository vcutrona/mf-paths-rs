# Multi-Feature Paths Composition and Recommendation
A recommender system for suggesting multi-feature paths based on user's interest.

## Getting Started

### Prerequisites

+ Python 2.7
+ PostgreSQL + PostGIS extension
+ Java

### Dependencies and external data sources

All Python dependencies are listed in the requirements.txt file.

The map inference algorithm that we used is publicly available on
[Github](https://github.com/pfoser/mapconstruction/tree/master/algorithms/Ahmed).

All raw trajectories available under the docs directory were download from [Wikiloc](https://www.wikiloc.com/).

## Running the application

A short demo is provided by the Demo class (under the main package).

You can also load our database dump in order to initialize your database.
The dump was made with pgAdmin III (v. 1.22) and is available under the postgis_dump directory.

### Algorithms Evaluation

Our experiments are available under the evaluation package. The Evaluator class
exposes methods for running the experiments and computing the nDCG measure.
The survey_results.csv file contains the users' answers that we collected through 
our survey.
Since the annotation task is stochastic, you should also load our database dump in order
to reproduce our experiment.

## Authors

* **Vincenzo Cutrona** - University of Milan-Bicocca - [vincenzo.cutrona@unimib.it](mailto:vincenzo.cutrona@unimib.it)