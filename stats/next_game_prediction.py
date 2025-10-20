import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.conf import settings
from .models import Game, Team, TeamStat
import datetime
import cfbd


class GamePredictor:
    """Predicts the outcome of the next game using Historical Data and a Random Forest Classifier."""

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=150, random_state=42, max_depth=10)
        self.scaler = StandardScaler()
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models')
        os.makedirs(self.model_path, exist_ok=True)

        # Cache for talent ratings
        self.talent_cache = {}
        self.ratings_cache = {}

    def get_team_talent(self, team_name, year):
        """Fetch team talent composite rating from CFBD API."""
        cache_key = f"{team_name}_{year}"
        if cache_key in self.talent_cache:
            return self.talent_cache[cache_key]

        try:
            configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
            with cfbd.ApiClient(configuration) as api_client:
                teams_api = cfbd.TeamsApi(api_client)
                talent = teams_api.get_talent(year=year)

                for t in talent:
                    # Correct attribute is 'team' not 'school'
                    if t.team == team_name:
                        self.talent_cache[cache_key] = t.talent
                        return t.talent
        except Exception as e:
            print(f"Error fetching talent for {team_name}: {e}")

        # Default talent rating if not found
        return 500.0  # Average FBS team talent

    def get_team_rating(self, team_name, year):
        """Fetch team SP+ rating from CFBD API."""
        cache_key = f"{team_name}_{year}"
        if cache_key in self.ratings_cache:
            return self.ratings_cache[cache_key]

        try:
            configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
            with cfbd.ApiClient(configuration) as api_client:
                ratings_api = cfbd.RatingsApi(api_client)
                # Correct method is get_sp (not get_sp_ratings)
                sp_ratings = ratings_api.get_sp(year=year)

                for r in sp_ratings:
                    if r.team == team_name:
                        rating = r.rating if r.rating else 0.0
                        self.ratings_cache[cache_key] = rating
                        return rating
        except Exception as e:
            print(f"Error fetching rating for {team_name}: {e}")

        return 0.0  # Neutral rating if not found

    def get_recruiting_rank(self, team_name, year):
        """Fetch team recruiting ranking from CFBD API."""
        try:
            configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
            with cfbd.ApiClient(configuration) as api_client:
                recruiting_api = cfbd.RecruitingApi(api_client)
                # Correct method is get_team_recruiting_rankings
                rankings = recruiting_api.get_team_recruiting_rankings(year=year)

                for r in rankings:
                    if r.team == team_name:
                        return r.rank if r.rank else 65
        except Exception as e:
            print(f"Error fetching recruiting rank for {team_name}: {e}")

        return 65  # Average FBS ranking

    def prepare_features(self, game, team_name="Oklahoma"):
        """Extract features from a game for prediction."""
        features = {}

        # Determine if Oklahoma is home or away
        is_oklahoma_home = game.home_team and game.home_team.name == team_name
        oklahoma_team = Team.objects.filter(name=team_name).first()

        # Get opponent name
        if is_oklahoma_home:
            opponent_team = game.away_team
            opponent_name = game.away_team.name if game.away_team else ""
        else:
            opponent_team = game.home_team
            opponent_name = game.home_team.name if game.home_team else ""

        # Get game year
        game_year = game.season if game.season else game.date.year

        if is_oklahoma_home:
            oklahoma_prev_games = Game.objects.filter(
                home_team=oklahoma_team,
                date__lt=game.date,
                home_points__isnull=False
            ).order_by('-date')[:5]
            opponent_prev_games = Game.objects.filter(
                away_team=game.away_team,
                date__lt=game.date,
                away_points__isnull=False
            ).order_by('-date')[:5]
        else:
            oklahoma_prev_games = Game.objects.filter(
                away_team=oklahoma_team,
                date__lt=game.date,
                away_points__isnull=False
            ).order_by('-date')[:5]
            opponent_prev_games = Game.objects.filter(
                home_team=game.home_team,
                date__lt=game.date,
                home_points__isnull=False
            ).order_by('-date')[:5]

        # Calculate average scores
        oklahoma_scores = []
        for g in oklahoma_prev_games:
            if g.home_team == oklahoma_team:
                oklahoma_scores.append(g.home_points or 0)
            else:
                oklahoma_scores.append(g.away_points or 0)

        opponent_scores = []
        for g in opponent_prev_games:
            if g.home_team == opponent_team:
                opponent_scores.append(g.home_points or 0)
            else:
                opponent_scores.append(g.away_points or 0)

        oklahoma_avg_score = np.mean(oklahoma_scores) if oklahoma_scores else 21.0
        opponent_avg_score = np.mean(opponent_scores) if opponent_scores else 21.0

        features['oklahoma_avg_score'] = oklahoma_avg_score
        features['opponent_avg_score'] = opponent_avg_score
        features['score_differential'] = oklahoma_avg_score - opponent_avg_score

        # Home field advantage
        features['is_home'] = 1 if is_oklahoma_home else 0

        # Calculate win percentages
        oklahoma_wins = sum(
            1 for g in oklahoma_prev_games
            if (g.home_team == oklahoma_team and g.home_points > g.away_points) or
               (g.away_team == oklahoma_team and g.away_points > g.home_points)
        )
        opponent_wins = sum(
            1 for g in opponent_prev_games
            if (g.home_team == opponent_team and g.home_points > g.away_points) or
               (g.away_team == opponent_team and g.away_points > g.home_points)
        )

        features['oklahoma_win_pct'] = oklahoma_wins / len(oklahoma_prev_games) if oklahoma_prev_games else 0.5
        features['opponent_win_pct'] = opponent_wins / len(opponent_prev_games) if opponent_prev_games else 0.5

        # Recent form (last 3 games)
        recent_oklahoma = list(oklahoma_prev_games[:3])
        oklahoma_recent_wins = sum(
            1 for g in recent_oklahoma
            if (g.home_team == oklahoma_team and g.home_points > g.away_points) or
               (g.away_team == oklahoma_team and g.away_points > g.home_points)
        )
        features['oklahoma_recent_form'] = oklahoma_recent_wins / len(recent_oklahoma) if recent_oklahoma else 0.5

        # Conference game indicator
        features['is_conference_game'] = 1 if game.conference_game else 0

        # Season progression (early season vs late season)
        features['week_number'] = game.week if game.week else 1

        # === NEW TALENT & RATING FEATURES ===

        # Team talent composite (247Sports talent composite)
        oklahoma_talent = self.get_team_talent(team_name, game_year)
        opponent_talent = self.get_team_talent(opponent_name, game_year)
        features['oklahoma_talent'] = oklahoma_talent
        features['opponent_talent'] = opponent_talent
        features['talent_differential'] = oklahoma_talent - opponent_talent

        # SP+ Ratings (advanced analytics rating)
        oklahoma_rating = self.get_team_rating(team_name, game_year)
        opponent_rating = self.get_team_rating(opponent_name, game_year)
        features['oklahoma_sp_rating'] = oklahoma_rating
        features['opponent_sp_rating'] = opponent_rating
        features['rating_differential'] = oklahoma_rating - opponent_rating

        # Recruiting rankings (talent pipeline indicator)
        oklahoma_recruiting = self.get_recruiting_rank(team_name, game_year)
        opponent_recruiting = self.get_recruiting_rank(opponent_name, game_year)
        features['oklahoma_recruiting_rank'] = oklahoma_recruiting
        features['opponent_recruiting_rank'] = opponent_recruiting
        features['recruiting_advantage'] = opponent_recruiting - oklahoma_recruiting  # Lower is better

        return features

    def clean_training_data(self, games):
        """Clean and validate training data."""
        cleaned_games = []
        for game in games:
            # Only include games with valid scores
            if game.home_points is None or game.away_points is None:
                continue

            # Only include games with valid teams
            if not game.home_team or not game.away_team:
                continue

            # Only include games with valid dates
            if not game.date:
                continue

            cleaned_games.append(game)

        return cleaned_games

    def train_model(self, team_name="Oklahoma", year=2025):
        """Train the model on historical game data."""
        # Get Oklahoma team
        oklahoma_team = Team.objects.filter(name=team_name).first()
        if not oklahoma_team:
            raise ValueError(f"Team '{team_name}' not found in database")

        # Get all completed games involving Oklahoma
        games = Game.objects.filter(
            season__lte=year,
            home_points__isnull=False,
            away_points__isnull=False
        ).filter(
            models.Q(home_team=oklahoma_team) | models.Q(away_team=oklahoma_team)
        ).order_by('date')

        # Clean the data
        games = self.clean_training_data(games)

        if len(games) < 5:
            raise ValueError(f"Not enough historical data to train model. Found {len(games)} games, need at least 5")

        # Prepare training data
        X = []
        y = []
        feature_names = None

        for game in games:
            try:
                features = self.prepare_features(game, team_name)
                if feature_names is None:
                    feature_names = list(features.keys())

                X.append(list(features.values()))

                # Target: 1 if Oklahoma won, 0 if Oklahoma lost
                is_oklahoma_home = game.home_team == oklahoma_team
                oklahoma_won = (is_oklahoma_home and game.home_points > game.away_points) or \
                               (not is_oklahoma_home and game.away_points > game.home_points)
                y.append(1 if oklahoma_won else 0)
            except Exception as e:
                print(f"Error processing game {game.id}: {e}")
                continue

        if len(X) < 5:
            raise ValueError(f"Not enough valid training samples. Got {len(X)} samples")

        X = np.array(X)
        y = np.array(y)

        # Handle edge case: if all games are wins or all are losses
        if len(np.unique(y)) < 2:
            print("Warning: Training data contains only one class. Model may not be accurate.")

        # Split and train (if we have enough data)
        if len(X) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            # Use all data for training if we don't have enough for a split
            X_train = X_test = X
            y_train = y_test = y

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model.fit(X_train_scaled, y_train)

        # Get accuracy
        train_accuracy = self.model.score(X_train_scaled, y_train)
        test_accuracy = self.model.score(X_test_scaled, y_test)

        # Save model and scaler
        joblib.dump(self.model, os.path.join(self.model_path, 'game_predictor.pkl'))
        joblib.dump(self.scaler, os.path.join(self.model_path, 'scaler.pkl'))
        joblib.dump(feature_names, os.path.join(self.model_path, 'feature_names.pkl'))

        return {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'games_trained': len(games),
            'feature_names': feature_names
        }

    def load_model(self):
        """Load saved model and scaler."""
        model_file = os.path.join(self.model_path, 'game_predictor.pkl')
        scaler_file = os.path.join(self.model_path, 'scaler.pkl')

        if os.path.exists(model_file) and os.path.exists(scaler_file):
            self.model = joblib.load(model_file)
            self.scaler = joblib.load(scaler_file)
            return True
        return False

    def predict_next_game(self, team_name="Oklahoma"):
        """Predict the outcome of Oklahoma's next game."""
        # Get Oklahoma team
        oklahoma_team = Team.objects.filter(name=team_name).first()
        if not oklahoma_team:
            return None

        # Get next scheduled game for Oklahoma
        today = datetime.date.today()
        next_game = Game.objects.filter(
            home_team=oklahoma_team,
            date__gte=today,
            home_points__isnull=True
        ).order_by('date').first()

        if not next_game:
            # Try away games
            next_game = Game.objects.filter(
                away_team=oklahoma_team,
                date__gte=today,
                away_points__isnull=True
            ).order_by('date').first()

        if not next_game:
            return None

        # Load or train model
        if not self.load_model():
            try:
                print("No trained model found. Training new model...")
                self.train_model(team_name)
            except Exception as e:
                print(f"Error training model: {e}")
                return None

        # Get features
        try:
            features = self.prepare_features(next_game, team_name)
            X = np.array([list(features.values())])
            X_scaled = self.scaler.transform(X)

            # Predict
            prediction = self.model.predict(X_scaled)[0]
            probability = self.model.predict_proba(X_scaled)[0]

            is_oklahoma_home = next_game.home_team == oklahoma_team
            opponent_name = next_game.away_team.name if is_oklahoma_home else next_game.home_team.name

            # Determine winner and win probability
            if prediction == 1:
                predicted_winner = team_name
                win_probability = probability[1] * 100
            else:
                predicted_winner = opponent_name
                win_probability = probability[0] * 100

            return {
                'game': next_game,
                'predicted_winner': predicted_winner,
                'win_probability': win_probability,
                'confidence': max(probability) * 100,
                'features': features,
                'opponent': opponent_name,
                'is_home': is_oklahoma_home
            }
        except Exception as e:
            print(f"Error making prediction: {e}")
            return None


# Import Django models Q for filtering
from django.db import models
