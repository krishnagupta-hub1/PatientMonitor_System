Steps to perform :

conda activate myenvv for all terminals 

1st Terminal : python collector_fastapi.py

terminals for required patient each : 
example for 3 patients :

# Patient 1
python simulation.py --patient-id patient-1 --rate 0.2

# Patient 2
python simulation.py --patient-id patient-2 --rate 0.2

# Patient 3
python simulation.py --patient-id patient-3 --rate 0.2

Next open the local host : http://localhost:8000/static/dashboard.html
Then to analyse metrics :python metrics_collector.py
