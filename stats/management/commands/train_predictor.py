from django.core.management.base import BaseCommand
from stats.next_game_prediction import GamePredictor


class Command(BaseCommand):
    help = 'Train the machine learning model for game prediction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--team',
            type=str,
            default='Oklahoma',
            help='Team name to train the model for (default: Oklahoma)'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2025,
            help='Season year to train up to (default: 2025)'
        )

    def handle(self, *args, **options):
        team = options['team']
        year = options['year']

        self.stdout.write(f"Training prediction model for {team}...")
        self.stdout.write(f"Using data up to {year} season\n")

        predictor = GamePredictor()

        try:
            results = predictor.train_model(team_name=team, year=year)

            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Model trained successfully!\n"
                f"  Games used for training: {results['games_trained']}\n"
                f"  Training accuracy: {results['train_accuracy']:.2%}\n"
                f"  Test accuracy: {results['test_accuracy']:.2%}\n"
            ))

            self.stdout.write("\nFeatures used:")
            for i, feature in enumerate(results['feature_names'], 1):
                self.stdout.write(f"  {i}. {feature}")

        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Unexpected error: {e}"))
            import traceback
            traceback.print_exc()

