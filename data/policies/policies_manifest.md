policies_manifest.md

RETOURS ET REMBOURSEMENTS

### returns_window
title:        Return window
scope:        Jusqu'à quand un client peut retourner un livre, et dans quel état.
owns:         30 jours à compter de la date de livraison
aliases:      too late to send it back, bought it months ago, how long do I have, missed the deadline, changed my mind, still eligible
referenced_by: return_request.yaml

### returns_process
title:        How to return an item
scope:        Les étapes concrètes d'un retour, qui paie le renvoi, où déposer le colis.
owns:         frais de renvoi (à la charge du client sauf erreur Bookly), format du numéro RMA
aliases:      twhere do I drop it off, who pays for postage, do I need a label, what do I do with the parcel, packaging, steps to give it back
referenced_by: return_request.yaml

### refund_timing
title:        Refund timing and method
scope:        Quand le client est remboursé, et sur quel moyen de paiement.
owns:         5 à 10 jours ouvrés après réception du retour
aliases:      when do I get my money, still waiting for the credit, nothing on my statement, back to my card, how long until reimbursed
referenced_by: return_request.yaml

### damaged_or_wrong_item
title:        Damaged or incorrect items
scope:        Ce qui se passe quand le livre reçu est abîmé ou n'est pas le bon. Escalade systématique.
owns:         aucun chiffre. Renvoie vers returns_window pour la fenêtre.
aliases:      arrived broken, torn cover, not what I ordered, different edition, pages missing, sent the wrong one
referenced_by: return_request.yaml


LIVRAISON

### shipping_times
title:        Delivery estimates
scope:        Délais annoncés par zone de livraison
owns:         FR 2-4 j ouvrés · BE/DE 3-6 j ouvrés · reste UE 5-9 j ouvrés
aliases:      when will it get here, how soon, arriving before Friday, is it quick, estimate for Belgium
referenced_by: order_status.yaml

### shipping_costs
title:        Delivery charges
scope:        Combien coûte la livraison et à partir de quel montant elle est offerte.
owns:         seuil de franco à 35 € · tarif standard 4,90 € FR, 5,90 € BE, 6,50 € DE
aliases:      free above, why was I charged extra, add another book to avoid, postage fee, does it cost anything to receive
referenced_by: retrieval only

### delayed_orders
title:        Late orders
scope:        A partir de quand une commande est officiellement en retard et ce que Bookly propose.
owns:         retard déclaré au-delà de 5 jours ouvrés après l'estimation haute
aliases:      hasn't moved in days, stuck, tracking says nothing, way past the estimate, never showed up
referenced_by: order_status.yaml

### order_cancellation
title:        Cancelling an order
scope:        Jusqu'à quel moment une commande peut être annulée.
owns:         annulation possible tant que le statut n'est pas shipped
aliases:      stop it before it leaves, don't send it, I made a mistake ordering, call it off, too late to cancel
referenced_by: order_status.yaml

COMPTE ET DIVERS

### password_reset
title:        Resetting a password
scope:        La procédure en libre-service et la durée de validité du lien.
owns:         lien valable 60 minutes
aliases:      can't log in, locked out, never got the email, link expired, forgot my details
referenced_by: retrieval only

### account_and_privacy
title:        Account data requests
scope:        Comment un client demande une copie ou la suppression de ses données.
owns:         réponse sous 30 jours à une demande d'accès
aliases:      delete everything about me, copy of what you hold, close my account, GDPR request, stop keeping my details
referenced_by: retrieval only

### preorders
title:        Pre-orders
scope:        Quand le client est débité, ce qui se passe si la date de sortie bouge, et la fenêtre de retour applicable.
owns:         débit à l'expédition, pas à la commande
aliases:      not out yet, release date moved, charged before it ships, book that isn't published, waiting for it to come out
referenced_by: retrieval only

### gift_cards
title:        Gift cards
scope:        Validité, remboursabilité, cumul avec une promotion
owns:         validité 24 mois, non remboursable en espèces
aliases:      voucher, can I get cash for it, expired code, use two at once, someone gave me a credit
referenced_by: retrieval only