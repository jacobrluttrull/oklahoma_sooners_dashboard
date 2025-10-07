# Oklahoma Sooners Dashboard — TODO List

This document outlines planned enhancements, polish tasks, and next-phase features for the Oklahoma Sooners Dashboard project.  
These updates build upon the current implementation (live stats, caching, and schedule display) and aim to expand data depth, improve visuals, and prepare the site for long-term scalability.

---

## Core Upcoming Tasks

1. Box Score for Latest Victory  
Goal: Display a detailed box score (passing, rushing, receiving leaders) for the most recent win.  
Implementation Plan:  
- Use the existing `latest_victory` object to retrieve its `id` or `game_id`.  
- Call:
game_stats = cfbd.GamesApi(api_client).get_game_stats(game_id)

text
- Extract key offensive stats and show in a new section on the homepage.  
- Consider a small table like:

| Player | Stat Type | Value |

2. Fix Time Formatting for Next Game  
Goal: Display the correct local game time with time zone adjustment.  
Implementation Plan:  
- Use:
next_game.start_date.astimezone(timezone.get_current_timezone())

text
- Display as:
{{ next_game.start_date|date:"l, F j, g:i A T" }}

text
- Add logic to handle None or “TBD” game times gracefully.

3. Add Rankings for Opponents  
Goal: Show team rankings next to opponents in both the schedule and latest victory.  
Implementation Plan:  
- Use:
rankings_api = cfbd.RankingsApi(api_client)
current_rankings = rankings_api.get_rankings(year=year)

text
- Create a mapping:
rankings = {team.team: team.rank for poll in current_rankings for team in poll.polls.ranks}

text
- Append opponent rank to schedule entries (e.g., “Texas (7)”).  
- Maintain a list of ranked wins for display:
ranked_wins = [g for g in schedule if g["result"] == "W" and g["opponent_rank"] <= 25]

text

4. Add Logo and Page Naming  
Goal: Give the site a more polished, branded presentation.  
Implementation Plan:  
- Place ou_logo.png in `/static/images/`.  
- Add to home.html header:
<img src="{% static 'images/ou_logo.png' %}" alt="Oklahoma Sooners Logo" width="120"> <h1>Oklahoma Sooners Football Dashboard</h1> ``` - Update Django page titles dynamically with context title.

## Additional Recommended Features

### Ranked Wins Summary
Goal: Track and display Oklahoma’s record against ranked opponents.  
Implementation Plan:
- Use the rankings data gathered above.
- Generate:
  - Ranked Record: 3–1
  - Ranked Wins: Texas (7), Alabama (12), LSU (23)

### Team Comparison Page
Goal: Create a separate page comparing Oklahoma’s core team stats against other SEC teams.  
Implementation Plan:
- Add route /compare/.
- Use CFBD StatsApi.get_team_season_stats() to pull offensive/defensive metrics.
- Visualize using a table or bar chart (points per game, yards, turnovers, etc.).

### Data Visualization
Goal: Add charts to enhance presentation and comprehension.  
Implementation Plan:
- Use Chart.js or Plotly.js via CDN in templates.
- Create visuals such as:
  - Season points per game over time.
  - Rushing vs. passing yard distribution.
  - Win margin trends.

### Persistent Historical Caching
Goal: Extend cache to preserve past season data across server restarts.  
Implementation Plan:
- Migrate to Redis for persistent caching.
- Cache historical data indefinitely (timeout=None).
- Allow browsing by year with a simple dropdown or route parameter.

### Theming and UI Improvements
Goal: Improve the visual design and responsiveness.  
Implementation Plan:
- Apply a minimalist dark theme or team-color theme (crimson and cream).
- Use CSS grid or Bootstrap for layout.
- Make tables responsive on mobile devices.

### Optional: API Rate Limit Handling
Goal: Ensure smooth operation even under CFBD API constraints.  
Implementation Plan:
- Wrap CFBD API calls in retry logic with exponential backoff.
- Display cached data if the API returns an error.

### Quality-of-Life Enhancements
- Add a “Last Updated” timestamp (already planned for caching transparency).
- Add tooltips or hover info for opponent rankings and stats.
- Include an “About” page explaining data sources and update frequency.
- Add favicon and meta description for browser and SEO polish.

---

## Notes for Next Work Session

- Start with Box Score for Latest Victory (foundation for deeper game detail pages).
- Move to Opponent Rankings (pairs perfectly with schedule improvements).
- End with visual polish (logos, title, page layout).
- Focus on one at a time — each task is modular and builds toward a full-featured, professional sports analytics dashboard.
