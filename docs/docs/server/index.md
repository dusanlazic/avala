---
hide:
- toc
---

# Avala server overview

The **Avala server** is responsible for a number of key tasks:

- Fetching and providing easy access to the latest flag IDs
- Keeping all configuration in a single place
- Synchronizing the attacks with the game ticks
- Automatic flag submission
- Real-time attack monitoring

---

This guide covers the complete setup of the Avala server and provides templates and real-world examples for each of the necessary files. By the end of this guide, you will have a single folder on your server containing all the required files with the following structure:

```
server-workspace/
├── avala.yaml
├── compose.yaml
├── flag_ids.py
└── submitter.py
```

As a first step, **create an empty folder on your server**. The next steps will guide you through the entire process of setting up the Avala server.

- [x] [Create an empty directory on your server](./index.md) ✅
- [ ] [Write the **submitter** script](./submitter.md) 👈
- [ ] [Write the **flag IDs fetching** script](./flag-ids.md)
- [ ] [Configure the Avala server](./configuration.md)
- [ ] [Launch all containers using Docker Compose](./launching.md)
