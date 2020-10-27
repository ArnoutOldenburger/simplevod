SimpleVoD Installation & Configuration 
============================
There are two daemons ( basically crontab script-jobs ) that act upon the database of the SimpleVod application.<br>
- The first one is called <b>SimplevodLoadDatabase.py</b> and is run during deployment and in case of major database changes ( such as adding new categories by the old-admin tool ).
- The second one is called <b>SimplevodUpdateDatabase.py</b> and periodically updates the database with new content from various socalled `Feeds`.<br>

After a regular installation ( the code is fetched from the Simplevod `GitHub`-repository ) both daemons can be found 
in the the following directory:
```
/srv/simplevod/database/
```
During installation a new PostgreSQL database `simplevod` is created. The <b>Load-</b>script ( <i>SimplevodLoadDatabase.py</i> ) uses a configuration file ( find file `config.json` in directory `/srv/simplevod/cfg` ) to read out data from a range of different data-sources and in a controlled way import this data it into various tables of the `simplevod` database.<br><br> 
Here below the functionality of the <b>Load-</b>-mechanism is described based on the content of `config.json` ( configuration flat-file with per `Feed` a set of paramaters  in json-format ):

| parameter            | values                                | description                                        |
| -------------------- | ------------------------------------- | -------------------------------------------------- |
| name                 | identifier                            | short-name for `Feed`                              |
| url                  | url to jsonld-vod-data file           | !! source must be `json` and <b>dir</b>-tag must be removed.                                                   |
| dir                  | path to location of xml-vod-data file or individual vod file | !! source must `xml` or `file` and <b>url</b>-tag must be removed.                                                   |
| style                | reference to css class-selector       | reference to stylesheet element for this `Feed`    |
| title                | none <sub>or</sub> full-name `Feed`               | in case source is `json` then full-name `Feed` is dereived from the `json` file itself <sub>or</sub> otherwise provide a full-name here |
| source               | json <sub>or</sub> xml <sub>or</sub> file                 |  three possible data-sources                       |
| category             | yes <sub>or</sub> no                            |  use category-layer in tv-menu                     |
| django               | yes <sub>or</sub> no                            |  use the new Django-style admin-tool               |
| load                 | yes <sub>or</sub> no                            |  `Feed` loaded or not                              |

Correspondence between `config.json` parameter and field in the `simplevod_feed` tabel of the `simplevod` database:

| config-parameter     | table-field                           | description                                        |
| -------------------- | ------------------------------------- | -------------------------------------------------- |
| name                 | name                                  | short-name identifier                              |
| url                  | url                                   | read (<i>feed/category/vod</i>) data form old admin-tool  |
| dir                  | xml                                   | read (<i>feed/category/vod</i>) data from xml file        |
| source               | retrieve                              | type of data: 0=feed not used;1=json;2=xml;3=file  |
| style                | style                                 | css styling for`Feed`                              |
| title                | title                                 | full-name `Feed`                                   |
| django               | is_django                             | TRUE=manage `Feed` with new admin-tool             |
| category             | use_category                          | TRUE=show categories;FALSE=only vods (source xml)  |
<br>
Next the functionality of the <b>Update-</b>-mechanism  ( by the <i>SimplevodUpdateDatabase.py</i> script ) is described:<br><br>
During deployment the <b>Update-</b>script is copied to the `/usr/local/bin`-directory and is scheduled as a `cronjob`.
Whenever it is executed its process is managed by the fields from the `simplevod_feed` tabel ( in the `simplevod` database ). Values of these fields correspond to how they were uploaded by the <b>Load-</b>script.<br>
Furthermore it is possible to adjust these settings with the help of the new admin-tool.

