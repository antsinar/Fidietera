# Πλατφόρμα Για Ιδιαίτερα σε Python

> Πλατφόρμα ενορχύστρωσης ατομικών `Python dev environments` για χρήση σε ιδιαίτερα μαθήματα. 


Προεγκατεστημένα πακέτα:
- JupyterLab
- Bpython
- jupyterlab-lsp
- python-lsp-server[rope, flake8, pylint]

Features:
- Ατομικές stateless Virtual Machines πίσω από τη πλατφόρμα του `fly.io`
- Υλοποίηση ασκήσεων και test
- Κοινός χώρος αποθήκευσης & read only πρόσβαση σε απαντήσεις άλλων
- Integration με github classroom / παρόμοιο service για αυτόματη βαθμολόγηση

Extras:
- Read-Only πρόσβαση σε επιλεγμένα αρχεία / τοποθεσίες

## Spin up container instance
```sh
# cd into project root
docker build -t fidietera --file docker/lab/Dockerfile .
# run image
docker run -it --rm -p 8888:8888 fidietera -d
# copy the link the link that looks like this and open window in browser
http://127.0.0.1:8888/lab?token=<token-here>
```