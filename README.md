# Rilevatore Consumo GAS manuale
Con questo package può essere creato un sensor template per l'inserimento del consumo del gas rilevabile dalla plancia energia.
Si compone di:
1. Package: "consumo_gas_1_0.yaml" (deve essere abilitata la cartella package se non già fatto);
2. Card: "card_consumo_gas_1_0" da inserire per rilevamento del dato;
3. Immagine: "rse.png" per abbellire la card, ma ovviamente può essere usata qualsiasi immagine a piacimento;
4. Visto che nei sensor template non è possibile prevedere lo state_class:
4a. Script: "add_state_class.py" (abilitare la cartella "python_scripts" in //config se non già fatto);
4b. Automazione: "Automazione.yaml" per inserire tramite lo script con un ritardo di 30 sec. lo stato "state_class: total_increasing" per il rilevamento della plancia.
Di seguito un esempio della CARD di rilevazione:
![image](https://github.com/stefanodr/Rilevatore-gas/assets/117826567/51d27855-8486-4476-957c-7f4099c1e72a)

