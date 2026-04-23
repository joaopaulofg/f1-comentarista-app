import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Race {
  session_key: number;
  meeting_name: string;
  country_name: string;
  circuit_short_name: string;
  date_start: string;
  year: number;
}

export interface DriverResult {
  position: number;
  driver_number: number;
  full_name: string;
  team_name?: string;
  points?: number;
}

export interface CommentaryResponse {
  session_key: number;
  race_title: string;
  podium: DriverResult[];
  full_results: DriverResult[];
  commentary: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = 'http://localhost:8001/api';

  constructor(private readonly http: HttpClient) {}

  getRecentRaces(): Observable<Race[]> {
    return this.http.get<Race[]>(`${this.baseUrl}/races/recent?limit=10`);
  }

  getCommentary(sessionKey: number): Observable<CommentaryResponse> {
    return this.http.get<CommentaryResponse>(`${this.baseUrl}/races/${sessionKey}/commentary`);
  }

  createCommentaryStream(sessionKey: number): EventSource {
    return new EventSource(`${this.baseUrl}/races/${sessionKey}/commentary/stream`);
  }
}
