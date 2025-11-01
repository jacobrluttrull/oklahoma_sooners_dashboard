# Oklahoma Sooners Dashboard - TODO List

**Last Updated:** October 31, 2025

---

## 🎯 High Priority Features

### 1. **Fill Empty Space on Home Page (Bottom Left)**

#### Option A: Quick Stats Comparison Card (RECOMMENDED)
**Location:** Below "Latest Victory" card on home page  
**Description:** Show how Oklahoma stacks up against SEC averages

**Implementation:**
- [ ] Create a new card component with title "Season Performance vs SEC"
- [ ] Calculate SEC averages from all SEC teams using existing `fetch_conference_standings` logic
- [ ] Display stats with visual indicators (🟢 above average, 🔴 below average, ⚪ at average)
- [ ] Include key metrics:
  - Points Per Game (OU vs SEC Avg)
  - Total Yards Per Game (OU vs SEC Avg)
  - Turnover Margin (OU vs SEC Avg)
  - Red Zone Efficiency (OU vs SEC Avg)
  - Third Down Conversion % (OU vs SEC Avg)

**Files to modify:**
- `stats/views.py` - Add SEC average calculations to home view
- `templates/stats/home.html` - Add new card below Latest Victory
- Styling already exists in base.html

**Data source:** Use existing `get_team_season_stats()` function

---

#### Option B: Upcoming Games Preview
**Location:** Below "Latest Victory" card on home page  
**Description:** Show next 2-3 games with quick opponent info

**Implementation:**
- [ ] Query next 3 upcoming games from database
- [ ] Display in compact list format:
  - Date & Time
  - Opponent (with logo)
  - Location
  - Opponent record/ranking
- [ ] Link to detailed opponent preview (future feature)

**Files to modify:**
- `stats/views.py` - Fetch next 3 games instead of just 1
- `templates/stats/home.html` - Add new card with upcoming games list

---

#### Option C: Team Achievements/Milestones
**Location:** Below "Latest Victory" card on home page  
**Description:** Highlight current achievements and approaching milestones

**Implementation:**
- [ ] Create achievement tracking logic
- [ ] Display current achievements:
  - Win streak (if active)
  - Notable season records
  - Player milestone tracker (e.g., "John Mateer 150 yards from 2,000 passing")
  - Team rankings (if top 25)
- [ ] Auto-update based on latest game data

**Files to modify:**
- `stats/views.py` - Add milestone calculation logic
- `stats/models.py` - Optional: Add Milestone model for tracking
- `templates/stats/home.html` - Add achievements card

---

### 2. **Player Stats Leaders Dashboard**
**Status:** 🆕 New Feature  
**Priority:** High  
**Description:** Show top performers across all categories

**Implementation:**
- [ ] Create new view at `/stats/players/`
- [ ] Display top 5 players in each category:
  - Passing: Yards, TDs, Completion %, QB Rating
  - Rushing: Yards, TDs, YPC
  - Receiving: Receptions, Yards, TDs
  - Defense: Tackles, Sacks, Interceptions
- [ ] Add filters: "This Season" vs "Last 5 Games"
- [ ] Include player photos/headshots (if available via API)

**Files to create:**
- `templates/stats/player_leaders.html`
- Update `stats/views.py` with player aggregation logic
- Update `stats/urls.py` to add new route
- Add navbar button for "Player Stats"

**Data source:** Aggregate from `PlayerStat` model

---

### 3. **Enhanced Team Stats Page**
**Status:** 📝 Currently Empty (stub exists)  
**Priority:** High  
**Description:** Build out the full team stats comparison page

**Implementation:**
- [ ] Calculate season averages for all stats
- [ ] Show Oklahoma stats vs SEC averages vs National averages
- [ ] Visual charts/graphs for key metrics (consider Chart.js or similar)
- [ ] Breakdowns by category:
  - Offensive Stats
  - Defensive Stats
  - Special Teams
  - Turnovers
  - Red Zone Efficiency
- [ ] Rankings within SEC and nationally
- [ ] Trend charts (performance over last 5 games)

**Files to modify:**
- `templates/stats/team_stats.html` (currently empty)
- `stats/views.py` - Implement team_stats view logic
- May need to aggregate data from multiple sources

---

## 🚀 Medium Priority Features

### 4. **Game-by-Game Performance Chart**
**Status:** 🆕 New Feature  
**Priority:** Medium  
**Description:** Visual timeline of season performance

**Implementation:**
- [ ] Create line/bar chart showing week-by-week performance
- [ ] Metrics to track:
  - Points scored vs points allowed per game
  - Total yards offense vs defense
  - Turnover differential per game
- [ ] Add to home page or team stats page
- [ ] Use Chart.js or similar lightweight charting library

**Files to modify:**
- `templates/stats/home.html` or create new section
- Add Chart.js CDN to base.html
- Query game-by-game stats from database

---

### 5. **Head-to-Head Comparison Tool**
**Status:** 🆕 New Feature  
**Priority:** Medium  
**Description:** Compare Oklahoma vs any opponent

**Implementation:**
- [ ] Create comparison page at `/stats/compare/`
- [ ] Dropdown to select opponent
- [ ] Display side-by-side stats:
  - Overall record
  - PPG offense/defense
  - Key statistical categories
  - Common opponents (if any)
  - Historical matchup record
- [ ] Useful for preview before big games

**Files to create:**
- `templates/stats/compare.html`
- Add comparison logic to views
- Update URLs

---

### 6. **Drive Charts & Play-by-Play (if API supports)**
**Status:** 🆕 New Feature  
**Priority:** Medium (depends on API availability)  
**Description:** Detailed drive and play analysis per game

**Implementation:**
- [ ] Check if CFBD API provides play-by-play data
- [ ] If available, create drive chart visualization
- [ ] Show scoring drives, time of possession per drive
- [ ] Add to boxscore page as expandable section

**Research needed:** Check CFBD API documentation for play-by-play endpoints

---

### 7. **Season Predictions & Playoff Chances**
**Status:** 🆕 New Feature  
**Priority:** Medium  
**Description:** Calculate remaining season outlook

**Implementation:**
- [ ] Show remaining schedule
- [ ] Calculate possible win/loss scenarios
- [ ] Display playoff probability (if ranked)
- [ ] Show what needs to happen for various outcomes
- [ ] Could integrate with Vegas odds if available

**Files to create:**
- `templates/stats/predictions.html`
- Prediction algorithm in views
- May require external data source for Vegas odds

---

## 🎨 UI/UX Enhancements

### 8. **Dark Mode Toggle**
**Status:** 🆕 New Feature  
**Priority:** Low-Medium  
**Description:** Add dark theme option

**Implementation:**
- [ ] Create dark theme CSS variables
- [ ] Add toggle button in navbar
- [ ] Save preference in localStorage
- [ ] Adjust all colors for dark mode readability
- [ ] Test on all pages

**Files to modify:**
- `templates/base.html` - Add dark theme styles and toggle script
- All template files - Test dark mode appearance

---

### 9. **Animations & Transitions**
**Status:** Enhancement  
**Priority:** Low  
**Description:** Add subtle animations for better UX

**Implementation:**
- [ ] Add fade-in animations for page loads
- [ ] Smooth transitions on stat cards
- [ ] Loading spinners for API calls
- [ ] Hover effects on interactive elements (already partially done)
- [ ] Win/Loss badge animations

**Files to modify:**
- `templates/base.html` - Add animation CSS
- Consider using animate.css or custom keyframes

---

### 10. **Mobile App-Style Navigation**
**Status:** Enhancement  
**Priority:** Low  
**Description:** Bottom nav bar for mobile users

**Implementation:**
- [ ] Create bottom navigation bar for mobile screens
- [ ] Icons for: Home, Standings, Stats, Schedule
- [ ] Fixed position at bottom
- [ ] Highlight active page
- [ ] Only show on screens < 768px

**Files to modify:**
- `templates/base.html` - Add mobile nav component

---

## 📊 Data & Backend Improvements

### 11. **Automatic Data Refresh Schedule**
**Status:** Enhancement  
**Priority:** Medium  
**Description:** Auto-update data without manual refresh

**Implementation:**
- [ ] Set up Celery or Django-Q for scheduled tasks
- [ ] Schedule daily refresh of:
  - Game scores (morning after game day)
  - Conference standings (every Monday)
  - Player stats (after each game)
- [ ] Add admin command to manually trigger refresh
- [ ] Log refresh history

**Files to create/modify:**
- `stats/tasks.py` - Celery tasks
- `requirements.txt` - Add Celery/Django-Q
- Setup Celery configuration

---

### 12. **Historical Season Data**
**Status:** 🆕 New Feature  
**Priority:** Low-Medium  
**Description:** View stats from previous seasons

**Implementation:**
- [ ] Add year selector dropdown on pages
- [ ] Store historical data in database
- [ ] Backfill previous seasons (2024, 2023, etc.)
- [ ] Allow comparison across seasons
- [ ] Show all-time records

**Files to modify:**
- Most templates - Add year selector
- Views - Filter by year parameter
- May need data migration to backfill

---

### 13. **Export Stats to PDF/CSV**
**Status:** 🆕 New Feature  
**Priority:** Low  
**Description:** Allow users to download stats

**Implementation:**
- [ ] Add "Export" button on stats pages
- [ ] Generate PDF reports (using ReportLab or WeasyPrint)
- [ ] Generate CSV downloads (using Python csv module)
- [ ] Include formatted tables and charts in PDF

**Files to create:**
- `stats/exports.py` - Export logic
- Add export views and URLs
- Requirements: reportlab, weasyprint

---

## 🔧 Technical Improvements

### 14. **Caching Layer**
**Status:** Enhancement  
**Priority:** Medium  
**Description:** Improve performance with caching

**Implementation:**
- [ ] Set up Django cache framework (Redis recommended)
- [ ] Cache API responses for 1 hour
- [ ] Cache rendered templates for frequently accessed pages
- [ ] Add cache invalidation on data refresh
- [ ] Reduces API calls and improves load times

**Files to modify:**
- `settings.py` - Configure cache backend
- `stats/views.py` - Add cache decorators
- `stats/cfb_api.py` - Cache API responses

---

### 15. **Error Handling & Logging**
**Status:** Enhancement  
**Priority:** Medium  
**Description:** Better error handling and logging

**Implementation:**
- [ ] Add comprehensive try/except blocks in API calls
- [ ] Log errors to file or monitoring service
- [ ] User-friendly error messages on frontend
- [ ] 404 and 500 error page templates
- [ ] Sentry integration for error tracking (optional)

**Files to modify:**
- `stats/cfb_api.py` - Add error handling
- `stats/views.py` - Catch and log errors
- Create custom error templates

---

### 16. **Unit Tests**
**Status:** 🆕 Testing  
**Priority:** Medium  
**Description:** Add test coverage

**Implementation:**
- [ ] Write tests for models
- [ ] Write tests for views
- [ ] Write tests for API calls (mock responses)
- [ ] Write tests for data processing logic
- [ ] Set up CI/CD to run tests automatically

**Files to create:**
- `stats/tests/test_models.py`
- `stats/tests/test_views.py`
- `stats/tests/test_api.py`
- `.github/workflows/tests.yml` (if using GitHub Actions)

---

### 17. **API Rate Limiting & Optimization**
**Status:** Enhancement  
**Priority:** Medium  
**Description:** Optimize API usage

**Implementation:**
- [ ] Implement request throttling
- [ ] Batch API requests where possible
- [ ] Monitor API usage quota
- [ ] Add retry logic with exponential backoff
- [ ] Display warning if approaching rate limit

**Files to modify:**
- `stats/cfb_api.py` - Add rate limiting logic

---

## 🎮 Fun Features

### 18. **Game Day Mode**
**Status:** 🆕 New Feature  
**Priority:** Low  
**Description:** Special UI on game days

**Implementation:**
- [ ] Detect if today is game day
- [ ] Show live score updates (if API supports)
- [ ] Countdown timer to kickoff
- [ ] Special banner/styling
- [ ] Push notifications for score changes (advanced)

**Files to modify:**
- `stats/views.py` - Detect game day
- `templates/base.html` - Game day banner/styling

---

### 19. **Fan Predictions & Polls**
**Status:** 🆕 New Feature  
**Priority:** Low  
**Description:** User engagement features

**Implementation:**
- [ ] Add user authentication (Django auth)
- [ ] Weekly game prediction form
- [ ] Leaderboard for most accurate predictions
- [ ] Polls: "Who will be player of the game?"
- [ ] Display community predictions

**Files to create:**
- `stats/models.py` - Add Prediction model
- `templates/stats/predictions_form.html`
- Add user authentication system

---

### 20. **Rivalry Tracker**
**Status:** 🆕 New Feature  
**Priority:** Low  
**Description:** Track records against rivals

**Implementation:**
- [ ] Define rivalry games (Texas, Texas A&M, etc.)
- [ ] Show all-time records against rivals
- [ ] Highlight rivalry game weeks
- [ ] Historical stats in rivalry matchups

**Files to create:**
- `templates/stats/rivalries.html`
- Add rivalry designation to teams/games

---

## 📱 Advanced Features (Future)

### 21. **Push Notifications**
**Status:** 🆕 Advanced  
**Priority:** Very Low  
**Description:** Browser push notifications for game updates

**Implementation:**
- [ ] Implement Web Push API
- [ ] Ask user permission for notifications
- [ ] Send notifications for:
  - Game start reminders
  - Final scores
  - Major plays (if live updates available)
- [ ] Allow users to configure notification preferences

**Requires:** Web Push service (OneSignal, Firebase Cloud Messaging, etc.)

---

### 22. **Voice Assistant Integration**
**Status:** 🆕 Advanced  
**Priority:** Very Low  
**Description:** "Hey Siri/Google, what was Oklahoma's score?"

**Implementation:**
- [ ] Research Alexa/Google Assistant integration
- [ ] Create voice-friendly API endpoint
- [ ] Return structured data for voice responses

**Requires:** Significant research and external service setup

---

## 🐛 Known Issues / Tech Debt

### 23. **Fix Warnings**
**Status:** Cleanup  
**Priority:** Low  
**Description:** Address IDE warnings

**Issues:**
- [ ] Obsolete `onerror` attribute on images (move to JavaScript)
- [ ] Unresolved template references warnings (minor, can ignore)
- [ ] CSS selectors never used warnings (clean up unused styles)

**Files to review:**
- All template files
- `templates/base.html`

---

### 24. **Requirements.txt Optimization**
**Status:** Cleanup  
**Priority:** Low  
**Description:** Ensure all dependencies are correct and minimal

**Tasks:**
- [ ] Review requirements.txt for unused packages
- [ ] Pin versions for all packages
- [ ] Add comments for what each package does
- [ ] Create dev-requirements.txt for development-only packages

---

### 25. **Database Optimization**
**Status:** Enhancement  
**Priority:** Low-Medium  
**Description:** Optimize database queries

**Tasks:**
- [ ] Add database indexes on frequently queried fields
- [ ] Use select_related/prefetch_related to reduce queries
- [ ] Run Django Debug Toolbar to identify N+1 queries
- [ ] Consider database query optimization for large datasets

**Files to modify:**
- `stats/models.py` - Add indexes
- `stats/views.py` - Optimize queries

---

## 📝 Documentation

### 26. **User Documentation**
**Status:** 🆕 Documentation  
**Priority:** Low  
**Description:** Create user guide

**Tasks:**
- [ ] Create user guide in README.md or separate docs
- [ ] Document all features
- [ ] Add screenshots
- [ ] Explain how to navigate the dashboard

---

### 27. **Developer Documentation**
**Status:** 🆕 Documentation  
**Priority:** Low  
**Description:** Document code and architecture

**Tasks:**
- [ ] Add docstrings to all functions
- [ ] Document data models
- [ ] Create architecture diagram
- [ ] Document API integration
- [ ] Add setup instructions for new developers

---

## 🎯 Quick Wins (Easy Implementations)

### Quick Win 1: Add Loading Spinners
- [ ] Show spinner while fetching data
- [ ] Use Bootstrap spinner or CSS animation
- [ ] Add to all pages that fetch API data

### Quick Win 2: Add Favicons
- [ ] Create Oklahoma Sooners favicon
- [ ] Add to base.html
- [ ] Include various sizes for different devices

### Quick Win 3: Add Meta Tags for SEO
- [ ] Add meta description
- [ ] Add Open Graph tags for social sharing
- [ ] Add Twitter card tags

### Quick Win 4: Add Footer
- [ ] Create footer with links
- [ ] Copyright notice
- [ ] Link to CFBD API (attribution)
- [ ] Contact/about page

### Quick Win 5: Breadcrumb Navigation
- [ ] Add breadcrumbs to pages
- [ ] Shows: Home > Team Stats > Oklahoma
- [ ] Improves navigation UX

---

## 💡 Ideas to Explore

- Weather data integration (weather at game time)
- Ticket price tracking (if available via API)
- Social media sentiment analysis (Twitter/X reactions)
- Fantasy football integration (if applicable)
- Recruiting tracker (track commits and rankings)
- Alumni stats tracker
- Historical all-time greats section
- Video highlights integration (YouTube API)
- Spotify playlist for game day
- Calendar export (add games to Google Calendar)

---

## 📊 Priority Summary

### Do First (High Priority):
1. ✅ Fill empty space on home page (Quick Stats Comparison)
2. ⬜ Build out Team Stats page
3. ⬜ Add Player Leaders dashboard
4. ⬜ Set up automatic data refresh

### Do Next (Medium Priority):
5. ⬜ Game-by-game performance chart
6. ⬜ Caching layer for performance
7. ⬜ Error handling improvements
8. ⬜ Head-to-head comparison tool

### Do Later (Low Priority):
9. ⬜ Dark mode toggle
10. ⬜ Historical season data
11. ⬜ Mobile app-style navigation
12. ⬜ Export to PDF/CSV

### Nice to Have (Very Low Priority):
13. ⬜ Push notifications
14. ⬜ Game day mode
15. ⬜ Fan predictions/polls
16. ⬜ Voice assistant integration

---

**Notes:**
- Start with filling the home page empty space (Option A recommended)
- Focus on completing core stats features before adding "fun" features
- Performance optimizations (caching, DB optimization) should come once more features are built
- User engagement features (predictions, polls) require authentication system first

**Estimated Total Development Time:** 40-60 hours for high + medium priority items

---

*Last updated: October 31, 2025*  
*Dashboard Version: 1.0*  
*Next Review: When you're more awake 😴*

