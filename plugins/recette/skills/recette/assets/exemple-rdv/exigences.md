# Exigences

| ID | Exigence | Critères d'acceptation | Priorité | Source |
|---|---|---|---|---|
| EX-001 | Un praticien se connecte avec son e-mail et son mot de passe ; un mot de passe faux est refusé sans dire si l'e-mail existe | Accès à l'agenda après connexion ; message d'erreur identique que le compte existe ou non | haute | US-12 |
| EX-002 | Le secrétariat crée un rendez-vous sur un créneau libre | Le rendez-vous apparaît dans l'agenda au statut « À confirmer » ; un créneau occupé ne peut pas être réservé deux fois | haute | US-15 |
| EX-003 | Annuler un rendez-vous confirmé libère le créneau et envoie un SMS d'annulation au patient | Statut « Annulé » ; créneau de nouveau libre ; SMS contenant « annulé », la date et l'heure, envoyé dans la minute | haute | US-21 |
| EX-004 | Chaque patient reçoit un SMS de rappel la veille de son rendez-vous, à 18 h | Un SMS par rendez-vous non annulé du lendemain, envoyé à 18 h ; aucun pour les annulés | moyenne | US-22 |
| EX-005 | L'agenda du jour s'exporte en CSV | CSV en UTF-8, séparateur « ; », une ligne par rendez-vous affiché | basse | US-30 |
| EX-006 | Les données d'une journée sont restaurables depuis la sauvegarde de la nuit, après la migration de schéma de la 1.4.0 | Restauration complète sur un cluster de recette en moins de 30 min ; nombre de rendez-vous identique à la source | haute | Exploitation, ADR-0003 |
