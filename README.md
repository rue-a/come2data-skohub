# Destatis Fächersystematiken -- Come2Data Version

In diesem Repositorium werden die Come2Data Versionen der Destatis Fächersystematiken verwaltet. Die Systematiken werden mit [SkoHub-Pages](https://github.com/skohub-io/skohub-pages) als interaktive Webseiten zur Erkundung unter https://rue-a.github.io/come2data-skohub/ bereitgestellt.

## Systematik der Fächergruppen, Lehr- und Forschungsbereiche und Fachgebiete (`personal_23`)

Referenz: https://www.destatis.de/DE/Methoden/Klassifikationen/Bildung/personal-stellenstatistik

Die Fächersystematik hat 3 Hierarchielevel:
1) Fächergruppe (FG), 2-stellige Id
2) Lehr- und Forschungsbereiche (LuF), 3-stellige Id
3) Fachgebiet (FGB), 4-stellige Id

Eine maschinenlesbare Version der Fächersystematik wurde von Destatis auf Anfrage in Form von Excel Workbooks bereitgestellt.

### Erstellung des SKOS Dokuments `destatis_personal_skos.ttl`

Das SKOS Dokument wurde mithile der Python Scripts `pers_tables2skos.py` 

#### 1) Konvertierung der Originaldaten zu SKOS


Als Eingangsdaten wurden CSV-Versionen der Originaldaten (Excel Workbooks) verwendent, bei denen einige händische Änderung vorgenommen wurden:
1) Etwaige Header mit Metainformationen wurden entfernt
2) Die zweite Spalte jeder Datei wurde gelöscht (da etwas unklar ist was sie bedeutet oder leer ist)
3) die verbleibenden Spalten wurden umbenannt in `id`, `label` und `parent_id` (`parent_id` kommt nur bei LuF und FGB vor)


#### 2) Übersetzung

Unter https://doi.org/10.5281/zenodo.10401074 ist eine englische Übersetzung der Vorgängerversion der Fächersystematik veröffentlicht (Guescini, R. (2023). DESTATIS Fächerklassifikation Translation Service (2.2). Zenodo. https://doi.org/10.5281/zenodo.10401074); sie liegt in der Datei `faecherklassifikation_skos_en.ttl` vor. Übersetzungen für Konzepte die nicht in dieser Vorgängerversion enthalten waren, wurden in `missing_translations.csv` mittels ChatGPT ergänzt. 

## Systematik der Fächergruppen, Studienbereiche und Studienfächer (`studierende_23`)

Referenz: https://www.destatis.de/DE/Methoden/Klassifikationen/Bildung/studenten-pruefungsstatistik

Die Fächersystematik hat 3 Hierarchielevel:
1) Fächergruppe (FG), 2-stellige Id
2) Studienbereiche (STB), 2-stellige Id
3) Studienfächer (STF), 3-stellige Id

Eine maschinenlesbare Version der Fächersystematik wurde von Destatis auf Anfrage in Form von Excel Workbooks bereitgestellt.

### Erstellung des Dokuments `destatis_studierende_skos.ttl`

Das SKOS Dokument wurde mithile der Python Scripts `stud_tables2skos.py` 

#### 1) Konvertierung der Originaldaten zu SKOS


Als Eingangsdaten wurden CSV-Versionen der Originaldaten (Excel Workbooks) verwendent, bei denen einige händische Änderung vorgenommen wurden:
1) Etwaige Header mit Metainformationen wurden entfernt
2) Die zweite Spalte jeder Datei wurde gelöscht (da etwas unklar ist was sie bedeutet oder leer ist)
3) Die verbleibenden Spalten wurden umbenannt in `id`, `label` und `parent_id` (`parent_id` kommt nur bei STB und STF vor)

Die Tabelle mit den Studienfächern (`Studienfach_WS2024.xlsx`/`stf.csv`) enthält ein Mapping der Studienfächer zum International Standard Classification of Education (ISCED). Die Konzepte des ISCED auf der Studienfachebene sind veröffentlicht unter der URL https://publications.europa.eu/resource/authority/snb/isced-f/<4-stellige-isced-id> (z.B.: https://publications.europa.eu/resource/authority/snb/isced-f/0220). Dieses Mapping wird mittel `skos:exactMatch` erfasst.

#### 2) Übersetzung

Eine SKOS-Version der *Systematik der Fächergruppen, Studienbereiche und Studienfächer* wird von der [DINI (Deutsche Initiative für Netzwerkinformation)](https://dini.de/) Arbeitsgruppe [KIM (Das Kompetenzzentrum Interoperable Metadaten)](https://dini.de/standards) unter https://github.com/dini-ag-kim/hochschulfaechersystematik gepflegt. Diese Version beinhaltet auch Übersetzungen der Konzeptlabels ins Englische und Ukrainische. Die Version wurde diesem Repositorium in der Version `v2025-02-03` als `hochschulfaechersystematik.ttl` hinzugefügt. 