import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ApiService, Race } from '../../services/api.service';

@Component({
  selector: 'app-race-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './race-list.component.html',
})
export class RaceListComponent implements OnInit {
  @Input() selectedSessionKey?: number;
  @Output() raceSelected = new EventEmitter<Race>();

  races: Race[] = [];
  loading = false;
  error = '';

  constructor(private readonly apiService: ApiService) {}

  ngOnInit(): void {
    this.loading = true;
    this.apiService.getRecentRaces().subscribe({
      next: (races) => {
        this.races = races;
        this.loading = false;
      },
      error: () => {
        this.error = 'Falha ao carregar as corridas.';
        this.loading = false;
      },
    });
  }

  selectRace(race: Race): void {
    this.raceSelected.emit(race);
  }
}
