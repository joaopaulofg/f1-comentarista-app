import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { RaceListComponent } from './components/race-list/race-list.component';
import { RaceCommentaryComponent } from './components/race-commentary/race-commentary.component';
import { Race } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RaceListComponent, RaceCommentaryComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {
  selectedRace?: Race;

  onRaceSelected(race: Race): void {
    this.selectedRace = race;
  }
}
