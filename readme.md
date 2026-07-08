# Pathfinder 1e Web Character
This Project shall provide a multilingual Pathfinder (at least german) web site. It will be designed to server the players as an easy to handle tool for
- character creation
- character leveling
- playing

The whole system will be designed in a way, only currently relevant elements are added. If this are classes, feats or spells.

**The System is designed to run only local**
# Architecture
The system posesses of serveral parts:
- Web UI for Player interaction
- Backend service to serve the frontend and store the data
- Database

Backend and Database are created as docker images for easy migration between systems.

As this is created as local only system, without any valid data, beside of the username, there is no security done by intention.
# Database
The Database is heart of the backend. For this it is composed of tree main parts:
- Definitions (Classes, Feats, etc.)
- Character data (Name, Stats, etc.)
- descriptions


## Explaination
One, and only one to zero or many: ||--o{
One to zero or |o--o{

```mermaid
erDiagram
    BaseClasses ||--o{ BaseClassLevelAbility: has
    BaseClasses {
        uuid id
        uuid arch_class_of
        int hit_dice
        bool wil_save
        bool fort_save
        bool ref_save
        float bab_progression
        string name
        string role
    }
    BaseClasses |o--o{ BaseClasses:has
    BaseClassLevelAbility ||--o{ BaseClassAbilites : provies
    BaseClassLevelAbility {
        uuid class_id
        uuid ability_id
        int level
        string type
        string description
        string name
    }
    BaseSkill {
        uuid id
        uuid attribute_id
        string nameCharacterLevel
        string description
    }
    BaseClassSkill  {
        uuid skill_id
        uuid class_id
    }
    BaseAttribute   {
        uuid id
        string name
    }
    BaseRace {
        uuid id
        data multiplyer_weight
    }
    BaseRacialFeat    {
        uuid id
        string name
        string description
    }
    BaseRacialFeatReplacement    {
        uuid racial_feat_id
        uuid replaces_racial_feat_id
    }
    BaseRaceAbility    {
        race_id
        racial_feat_id
    }
    BaseFeat {
        uuid id 
        string name
        string description
    }
    BaseRequirements {
        uuid requirement_id
    }
    BaseFeatRequirements{
        uuid requirement_id
        uuid feat_id
    }
    BaseRequiredFeat{
        uuid requirement_id
        uuid feat_id
    }
    BaseRequiredSkill{
        uuid requirement_id
        uuid skill_id
        int value
    }
    BaseRequiredClass{
        uuid requirement_id
        uuid class_id
        int value
    }
    User {
        uuid id
        string name
    }
    Character {
        uuid id
        uuid user_id
        uuid prefered_class
        int current_hit_points
        string name
    }
    Character ||--o{ BaseClasses : has
    Character ||--o{ User:has
    CharacterAttribute {
        uuid attribute_id
        uuid character_level_id
        int value
    }
    Character ||--o{ Attribute :has
    CharacterLevel{
        uuid id
        int level
        uuid character_id
        uuid base_class_id
        int hit_points
    }
    CharacterSkill{
        uuid level_id
        uuid skill_id
        int skill_points
    }
    CharacterFeat{
        uuid level_id
        uuid feat_id
    }
```