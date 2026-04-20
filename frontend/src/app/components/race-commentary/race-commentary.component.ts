import { Component, Input, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ApiService, CommentaryResponse, Race } from '../../services/api.service';

@Component({
  selector: 'app-race-commentary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './race-commentary.component.html',
})
export class RaceCommentaryComponent implements OnChanges, OnDestroy {
  @Input() race?: Race;

  data?: CommentaryResponse;
  loading = false;
  error = '';
  progressIndex = 0;
  readonly progressSteps = [
    'Buscando dados finais da corrida',
    'Organizando pódio e top 10',
    'Escrevendo comentário em tempo real',
  ];

  private progressTimer?: number;
  private activeRequestId = 0;
  private commentaryStream?: EventSource;

  constructor(private readonly apiService: ApiService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes['race'] || !this.race) {
      return;
    }

    const requestId = ++this.activeRequestId;
    this.loading = true;
    this.error = '';
    this.data = undefined;
    this.progressIndex = 0;
    this.closeCommentaryStream();
    this.startProgressSimulation();

    const stream = this.apiService.createCommentaryStream(this.race.session_key);
    this.commentaryStream = stream;

    stream.addEventListener('metadata', (event: Event) => {
      if (requestId !== this.activeRequestId) {
        return;
      }

      const message = event as MessageEvent<string>;
      const response = JSON.parse(message.data) as CommentaryResponse;
      this.data = response;
      this.progressIndex = 1;
    });

    stream.addEventListener('chunk', (event: Event) => {
      if (requestId !== this.activeRequestId || !this.data) {
        return;
      }

      const message = event as MessageEvent<string>;
      const payload = JSON.parse(message.data) as { text?: string };
      if (!payload.text) {
        return;
      }

      this.progressIndex = 2;
      this.data = {
        ...this.data,
        commentary: `${this.data.commentary}${payload.text}`,
      };
    });

    stream.addEventListener('done', () => {
      if (requestId !== this.activeRequestId) {
        return;
      }

      this.loading = false;
      this.stopProgressSimulation();
      this.closeCommentaryStream();
    });

    stream.addEventListener('app-error', (event: Event) => {
      if (requestId !== this.activeRequestId) {
        return;
      }

      const message = event as MessageEvent<string>;
      let detail = 'Falha ao gerar o comentário.';

      if (typeof message.data === 'string' && message.data) {
        try {
          const payload = JSON.parse(message.data) as { detail?: string };
          if (payload.detail) {
            detail = payload.detail;
          }
        } catch {
          detail = 'Falha ao gerar o comentário.';
        }
      }

      this.error = detail;
      this.loading = false;
      this.stopProgressSimulation();
      this.closeCommentaryStream();
    });

    stream.onerror = () => {
      if (requestId !== this.activeRequestId) {
        return;
      }

      if (stream.readyState === EventSource.CLOSED && !this.loading) {
        this.closeCommentaryStream();
        return;
      }

      if (this.loading) {
        this.error = 'Conexão interrompida durante a geração do comentário.';
        this.loading = false;
        this.stopProgressSimulation();
      }

      this.closeCommentaryStream();
    };
  }

  ngOnDestroy(): void {
    this.stopProgressSimulation();
    this.closeCommentaryStream();
  }

  trackProgressStep(index: number): string {
    return this.progressSteps[index];
  }

  isProgressDone(index: number): boolean {
    return index < this.progressIndex;
  }

  isProgressActive(index: number): boolean {
    return this.loading && index === this.progressIndex;
  }

  private startProgressSimulation(): void {
    this.stopProgressSimulation();

    this.progressTimer = window.setInterval(() => {
      if (this.progressIndex < this.progressSteps.length - 1) {
        this.progressIndex += 1;
      }
    }, 1400);
  }

  private stopProgressSimulation(): void {
    if (this.progressTimer) {
      window.clearInterval(this.progressTimer);
      this.progressTimer = undefined;
    }
  }

  private closeCommentaryStream(): void {
    this.commentaryStream?.close();
    this.commentaryStream = undefined;
  }
}
