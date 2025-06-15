"""
One-Armed Bandit boss analysis for Liberation of Undermine.
"""

from typing import List
import pandas as pd
from datetime import datetime
import logging

from ..base import BossAnalysisBase
from ...plotting.base import NumberPlot, PercentagePlot

logger = logging.getLogger(__name__)


class OneArmedBanditAnalysis(BossAnalysisBase):
    """Analysis for One-Armed Bandit encounters in Liberation of Undermine."""

    def __init__(self, api_client):
        super().__init__(api_client)
        self.boss_name = "One-Armed Bandit"
        self.encounter_id = 3014
        self.difficulty = 5

    def analyze(self, report_codes: List[str]) -> None:
        """Analyze reports for One-Armed Bandit encounters."""
        logger.info(f"Starting One-Armed Bandit analysis for {len(report_codes)} reports")
        
        for report_code in report_codes:
            try:
                logger.info(f"Processing report {report_code}")
                self._process_report(report_code)
            except Exception as e:
                logger.error(f"Error processing report {report_code}: {e}")
                continue

    def _process_report(self, report_code: str) -> None:
        """Process a single report for One-Armed Bandit analysis."""
        logger.debug(f"Processing report {report_code} for One-Armed Bandit")
        
        # Get fights for this report
        fight_ids = self.get_fight_ids(report_code)
        if not fight_ids:
            return

        # Get timestamp of first fight
        start_time = self.get_start_time(report_code, fight_ids)

        report_results = {
            "starttime": start_time,
            "reportCode": report_code,
            "analysis": [],
            "fight_ids": fight_ids
        }

        # Get players who participated in these specific fights
        report_players = self.get_participants(report_code, fight_ids)
        if not report_players:
            return

        # Analyze different aspects of the report
        interrupts_data = self._analyze_overload_interrupts(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "Overload! Interrupts", "data": interrupts_data})

        uptime_data = self._analyze_high_roller_uptime(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "High Roller Uptime", "data": uptime_data})

        damage_data = self._analyze_damage_to_premium_dynamite_booties(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "Premium Dynamite Booties Damage", "data": damage_data})

        reel_assistants_data = self._analyze_damage_to_reel_assistants(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "Reel Assistants Damage", "data": reel_assistants_data})

        boss_damage_data = self._analyze_damage_to_boss(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "Boss Damage", "data": boss_damage_data})

        absorbed_damage_data = self._analyze_absorbed_damage_to_reel_assistants(report_code, fight_ids, report_players)
        report_results["analysis"].append({"name": "Absorbed Damage to Reel Assistants", "data": absorbed_damage_data})

        self.results.append(report_results)
        logger.info(f"Successfully processed report {report_code} with {len(report_results['analysis'])} analyses")

    def _analyze_overload_interrupts(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze interrupt events for Overload! ability."""
        return self.analyze_interrupts(
            report_code=report_code,
            fight_ids=fight_ids,
            report_players=report_players,
            ability_id=460582  # Overload! ability ID
        )

    def _analyze_high_roller_uptime(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze High Roller debuff uptime."""
        return self.analyze_debuff_uptime(
            report_code=report_code,
            fight_ids=fight_ids,
            report_players=report_players,
            ability_id=460444.0  # High Roller debuff ID
        )

    def _analyze_damage_to_premium_dynamite_booties(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze damage done to Premium Dynamite Booties."""
        # Use the base class method to get damage data
        damage_data = self.get_damage_to_actor(
            report_code=report_code,
            fight_ids=fight_ids,
            target_game_id=231027,  # Premium Dynamite Booty gameID
            report_players=report_players
        )

        # Rename the 'damage' field to match the expected column name
        for player_data in damage_data:
            player_data['damage_to_dynamite_booties'] = player_data.pop('damage')

        return damage_data

    def _analyze_damage_to_reel_assistants(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze damage done to Reel Assistants."""
        # Use the base class method to get damage data
        damage_data = self.get_damage_to_actor(
            report_code=report_code,
            fight_ids=fight_ids,
            target_game_id=228463,  # Reel Assistants gameID
            report_players=report_players
        )

        # Rename the 'damage' field to match the expected column name
        for player_data in damage_data:
            player_data['damage_to_reel_assistants'] = player_data.pop('damage')

        return damage_data

    def _analyze_damage_to_boss(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze damage done to Boss."""
        # Use the base class method to get damage data
        damage_data = self.get_damage_to_actor(
            report_code=report_code,
            fight_ids=fight_ids,
            target_game_id=228458,  # Boss gameID
            report_players=report_players
        )

        # Rename the 'damage' field to match the expected column name
        for player_data in damage_data:
            player_data['damage_to_boss'] = player_data.pop('damage')

        return damage_data

    def _analyze_absorbed_damage_to_reel_assistants(self, report_code: str, fight_ids, report_players) -> List:
        """Analyze absorbed damage done to Reel Assistants."""
        # Use the base class method to get absorbed damage data
        damage_data = self.get_damage_to_actor(
            report_code=report_code,
            fight_ids=fight_ids,
            target_game_id=228463,  # Reel Assistants gameID
            report_players=report_players,
            filter_expression="absorbedDamage > 0"
        )

        # Rename the 'damage' field to match the expected column name
        for player_data in damage_data:
            player_data['absorbed_damage_to_reel_assistants'] = player_data.pop('damage')

        return damage_data

    def generate_plots(self) -> None:
        """Generate plots for One-Armed Bandit analysis."""
        logger.info("Generating plots for One-Armed Bandit analysis")
        
        if not self.results:
            logger.warning("No reports available to generate plots")
            return

        # Sort reports by starttime (newest first)
        sorted_reports = sorted(self.results, key=lambda x: x['starttime'], reverse=True)
        latest_report = sorted_reports[0]
        report_date = datetime.fromtimestamp(latest_report['starttime']).strftime('%d.%m.%Y')

        # Get fight counts for current and previous reports
        current_fight_count = len(latest_report.get('fight_ids', []))
        previous_fight_count = len(sorted_reports[1].get('fight_ids', [])) if len(sorted_reports) > 1 else None

        # Generate Overload! Interrupts plot
        logger.debug("Generating Overload! Interrupts plot")
        self._generate_interrupts_plot(report_date, current_fight_count, previous_fight_count)
        
        # Generate High Roller Uptime plot
        logger.debug("Generating High Roller Uptime plot")
        self._generate_uptime_plot(report_date)
        
        # Generate Premium Dynamite Booties Damage plot
        logger.debug("Generating Premium Dynamite Booties Damage plot")
        self._generate_damage_plot(report_date, current_fight_count, previous_fight_count)
        
        # Generate Reel Assistants Damage plot
        logger.debug("Generating Reel Assistants Damage plot")
        self._generate_reel_assistants_damage_plot(report_date, current_fight_count, previous_fight_count)
        
        # Generate Boss Damage plot
        logger.debug("Generating Boss Damage plot")
        self._generate_boss_damage_plot(report_date, current_fight_count, previous_fight_count)
        
        # Generate Absorbed Damage to Reel Assistants plot
        logger.debug("Generating Absorbed Damage to Reel Assistants plot")
        self._generate_absorbed_damage_plot(report_date, current_fight_count, previous_fight_count)

    def _generate_interrupts_plot(self, report_date: str, current_fight_count: int, previous_fight_count: int) -> None:
        """Generate plot for Overload! interrupts."""
        current_data, previous_dict = self.find_analysis_data(
            "Overload! Interrupts",
            'interrupts',
            'player_name'
        )

        df = pd.DataFrame(current_data)
        interrupt_plot = NumberPlot(
            title="Overload! Interrupts",
            date=report_date,
            df=df,
            previous_data=previous_dict,
            value_column='interrupts',
            value_column_name='Interrupts',
            name_column='player_name',
            class_column='class',
            current_fight_count=current_fight_count,
            previous_fight_count=previous_fight_count
        )
        interrupt_plot.save()

    def _generate_uptime_plot(self, report_date: str) -> None:
        """Generate plot for High Roller uptime."""
        current_hr_data, previous_hr_dict = self.find_analysis_data(
            "High Roller Uptime",
            'uptime_percentage',
            'player_name'
        )
        
        hr_df = pd.DataFrame(current_hr_data)
        hr_plot = PercentagePlot(
            title="High Roller Uptime",
            date=report_date,
            df=hr_df,
            previous_data=previous_hr_dict,
            value_column='uptime_percentage',
            value_column_name='Uptime',
            name_column='player_name',
            class_column='class'
        )
        hr_plot.save()

    def _generate_damage_plot(self, report_date: str, current_fight_count: int, previous_fight_count: int) -> None:
        """Generate plot for Premium Dynamite Booties damage."""
        current_dmg_data, previous_dmg_dict = self.find_analysis_data(
            "Premium Dynamite Booties Damage",
            'damage_to_dynamite_booties',
            'player_name'
        )
        
        dmg_df = pd.DataFrame(current_dmg_data)
        dmg_plot = NumberPlot(
            title="Schaden auf Geschenke",
            date=report_date,
            df=dmg_df,
            previous_data=previous_dmg_dict,
            value_column='damage_to_dynamite_booties',
            value_column_name='Schaden',
            name_column='player_name',
            class_column='class',
            current_fight_count=current_fight_count,
            previous_fight_count=previous_fight_count
        )
        dmg_plot.save()

    def _generate_reel_assistants_damage_plot(self, report_date: str, current_fight_count: int, previous_fight_count: int) -> None:
        """Generate plot for Reel Assistants damage."""
        current_dmg_data, previous_dmg_dict = self.find_analysis_data(
            "Reel Assistants Damage",
            'damage_to_reel_assistants',
            'player_name'
        )
        
        dmg_df = pd.DataFrame(current_dmg_data)
        dmg_plot = NumberPlot(
            title="Schaden auf Reel Assistants",
            date=report_date,
            df=dmg_df,
            previous_data=previous_dmg_dict,
            value_column='damage_to_reel_assistants',
            value_column_name='Schaden',
            name_column='player_name',
            class_column='class',
            current_fight_count=current_fight_count,
            previous_fight_count=previous_fight_count
        )
        dmg_plot.save()

    def _generate_boss_damage_plot(self, report_date: str, current_fight_count: int, previous_fight_count: int) -> None:
        """Generate plot for Boss damage."""
        current_dmg_data, previous_dmg_dict = self.find_analysis_data(
            "Boss Damage",
            'damage_to_boss',
            'player_name'
        )
        
        dmg_df = pd.DataFrame(current_dmg_data)
        dmg_plot = NumberPlot(
            title="Schaden auf Boss",
            date=report_date,
            df=dmg_df,
            previous_data=previous_dmg_dict,
            value_column='damage_to_boss',
            value_column_name='Schaden',
            name_column='player_name',
            class_column='class',
            current_fight_count=current_fight_count,
            previous_fight_count=previous_fight_count
        )
        dmg_plot.save()

    def _generate_absorbed_damage_plot(self, report_date: str, current_fight_count: int, previous_fight_count: int) -> None:
        """Generate plot for absorbed damage to Reel Assistants."""
        current_dmg_data, previous_dmg_dict = self.find_analysis_data(
            "Absorbed Damage to Reel Assistants",
            'absorbed_damage_to_reel_assistants',
            'player_name'
        )
        
        dmg_df = pd.DataFrame(current_dmg_data)
        dmg_plot = NumberPlot(
            title="Absorbierter Schaden auf Reel Assistants",
            date=report_date,
            df=dmg_df,
            previous_data=previous_dmg_dict,
            value_column='absorbed_damage_to_reel_assistants',
            value_column_name='Absorbierter Schaden',
            name_column='player_name',
            class_column='class',
            current_fight_count=current_fight_count,
            previous_fight_count=previous_fight_count
        )
        dmg_plot.save()

