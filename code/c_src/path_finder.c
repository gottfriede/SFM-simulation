// gcc -shared -fPIC -o libpathfinder.dll path_finder.c
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <float.h>
#include <math.h>
#define max(a, b) (((a) > (b)) ? (a) : (b))

// Vector is an ordered dynamic array of pointers.
typedef struct {
	void **data;
	int capacity;
	int len;		// number of elements in this vector.
} Vector;

Vector * new_vec(int capacity)
{
	Vector *v = malloc(sizeof(Vector));
	v->capacity = capacity;
	v->data = (void *)malloc(sizeof(void *) * v->capacity);
	v->len = 0;	// number of elements in the vector.
	return v;
}

/* Pre-conditions: v != NULL, elem != NULL.
 * Post-conditions: elem is placed at the end of vector v.*/
void vec_put(Vector * v, void * elem)
{
	if (v->capacity == v->len) {
		v->capacity *= 2;
		v->data = realloc(v->data, sizeof(void *) * v->capacity);
	}
	v->data[v->len++] = elem;
}

/* Post-conditions: If v is NULL or index is out of bounds returns NULL
else returns v[index].*/
void * vec_get(Vector * v, int index)
{
	if (v == NULL || index < 0 || index >= v->len)
		return NULL;
	return v->data[index];
}

/* 0 <= index < v->len */
void vec_remove(Vector *v, int index)
{
	for (int i = index; i < v->len - 1; i++)
		v->data[i] = v->data[i + 1];
	v->len--;
}

void vec_remove_elem(Vector *v, void *elem)
{
	for (int i = 0; i < v->len; i++) {
		if (v->data[i] == elem) {
			vec_remove(v, i);
			return;
		}
	}
}

bool vec_is_in(Vector *v, void *elem)
{
	for (int i = 0; i < v->len; i++) {
		if (v->data[i] == elem)
			return true;
	}
	return false;
}

typedef struct Node Node;
typedef struct Node {
	int x, y;
	float f, g, h;
	Node *parent, *next;
	bool open, closed;
} Node;

int num_row;
int num_col;
int *grid;
Node *node_list;
Node *start;
Node *goal;

bool is_walkable_at(int x, int y)
{
	return 0 <= x && x < num_row && 0 <= y && y < num_col && grid[y + x * num_col] != 1;
}

Node *jump(int cx, int cy, int dx, int dy)
{
	int nx, ny;
	nx = cx + dx;
	ny = cy + dy;
	while (true) {
		if (!is_walkable_at(nx, ny))
			return NULL;
		if (nx == goal->x && ny == goal->y)
			return goal;
		// check for forced neighbors
		if (dx != 0 && dy != 0) {
			if ((is_walkable_at(cx, ny + dy) && !is_walkable_at(cx, ny)) 
				|| (is_walkable_at(nx + dx, cy) && !is_walkable_at(nx, cy)))
				return node_list + ny + nx * num_col;
			if (jump(nx, ny, dx, 0) != NULL || jump(nx, ny, 0, dy) != NULL)
				return node_list + ny + nx * num_col;
		}
		// horizontally/vertically
		else {
			if (dx != 0) {
				if ((is_walkable_at(nx + dx, ny + 1) && !is_walkable_at(nx, ny + 1))
					|| (is_walkable_at(nx + dx, ny - 1) && !is_walkable_at(nx, ny - 1)))
					return node_list + ny + nx * num_col;
			}
			else {
				if ((is_walkable_at(nx + 1, ny + dy) && !is_walkable_at(nx + 1, ny))
					|| (is_walkable_at(nx - 1, ny + dy) && !is_walkable_at(nx - 1, ny)))
					return node_list + ny + nx * num_col;
			}
		}
		cx = nx, cy = ny;
		nx = cx + dx;
		ny = cy + dy;
	}
}

Vector *find_neighbors(Node *node)
{
	int cx, cy;
	int px, py;
	int dx, dy;
	Vector *neighbors = new_vec(8);

	cx = node->x;
	cy = node->y;
	if (node->parent != NULL) {
		px = node->parent->x;
		py = node->parent->y;
		dx = (cx - px) / max(abs(cx - px), 1);
		dy = (cy - py) / max(abs(cy - py), 1);

		if (dx != 0 && dy != 0) {
			if (is_walkable_at(cx, cy + dy))
				vec_put(neighbors, (node_list + (cy + dy) + cx * num_col));
			if (is_walkable_at(cx + dx, cy))
				vec_put(neighbors, (node_list + cy + (cx + dx) * num_col));
			if (is_walkable_at(cx + dx, cy + dy))
				vec_put(neighbors, (node_list + (cy + dy) + (cx + dx) * num_col));
			// forced neighbors
			if (!is_walkable_at(cx - dx, cy))
				vec_put(neighbors, (node_list + (cy + dy) + (cx - dx) * num_col));
			if (!is_walkable_at(cx, cy - dy))
				vec_put(neighbors, (node_list + (cy - dy) + (cx + dx) * num_col));
		}
		else {
			if (dx == 0) {
				if (is_walkable_at(cx, cy + dy))
					vec_put(neighbors, (node_list + (cy + dy) + (cx) * num_col));
				if (!is_walkable_at(cx + 1, cy))
					vec_put(neighbors, (node_list + (cy + dy) + (cx + 1)* num_col));
				if (!is_walkable_at(cx - 1, cy))
					vec_put(neighbors, (node_list + (cy + dy) + (cx - 1)* num_col));
			}
			else {
				if (is_walkable_at(cx + dx, cy))
					vec_put(neighbors, (node_list + (cy) + (cx + dx)* num_col));
				if (!is_walkable_at(cx, cy + 1))
					vec_put(neighbors, (node_list + (cy + 1)+(cx + dx)* num_col));
				if (!is_walkable_at(cx, cy - 1))
					vec_put(neighbors, (node_list + (cy - 1) + (cx + dx)* num_col));
			}
		}
	}
	else { // no parent
		int xs[] = { -1, 0, 1, -1, 1, -1, 0, 1 };
		int ys[] = { -1, -1, -1, 0, 0, 1, 1, 1 };
		for (int i = 0; i < 8; i++) {
			int nx = cx + xs[i];
			int ny = cy + ys[i];
			if (is_walkable_at(nx, ny))
				vec_put(neighbors, node_list + ny + nx * num_col);
		}
	}
	return neighbors;
}

float dist_between(Node *n1, Node *n2)
{
	if (n1->x == n2->x || n1->y == n2->y)
		return 1.0;
	return 1.4;
}

float heuristic_estimate(Node *start, Node *goal)
{
	return abs(start->x - goal->x) + abs(start->y - goal->y);
}

void identify_successors(Node *node, Vector *open_list)
{
	Vector *neighbors = find_neighbors(node);
	Node *neighbor, *jump_node;
	int dx, dy;
	float cost;

	for (int i = 0; i < neighbors->len; i++) {
		neighbor = vec_get(neighbors, i);
		dx = neighbor->x - node->x;
		dy = neighbor->y - node->y;
		jump_node = jump(node->x, node->y, dx, dy);
		if (jump_node != NULL && !jump_node->closed) {
			cost = node->g + dist_between(node, neighbor);
			if (!jump_node->open || cost < jump_node->g) {
				jump_node->g = cost;
				jump_node->h = heuristic_estimate(jump_node, goal);
				jump_node->f = jump_node->g + jump_node->h;
				jump_node->parent = node;
				if (!jump_node->open) {
					vec_put(open_list, jump_node);
					jump_node->open = true;
				}
			}
		}
	}
}

void construct_path()
{
	Node *node = goal;
	while (node->parent) {
		node->parent->next = node;
		node = node->parent;
	}
}

Node *get_lowest(Vector *open_list)
{
	float lowest = FLT_MAX;
	Node *lowest_node = NULL;
	Node *node;
	for (int i = 0; i < open_list->len; i++) {
		node = vec_get(open_list, i);
		if (node->f < lowest) {
			lowest = node->f;
			lowest_node = node;
		}
	}
	return lowest_node;
}

void a_star()
{
	Vector *open_list = new_vec(16);
	Node *current;
	vec_put(open_list, start);
	start->g = 0;
	start->f = start->g + heuristic_estimate(start, goal);
	start->open = true;
	while (open_list->len != 0) {
		current = get_lowest(open_list);
		if (current == goal) {
			construct_path();
			return;
		}
		vec_remove_elem(open_list, current);
		current->open = false;
		current->closed = true;
		identify_successors(current, open_list);
	}
}

void get_direction(int _grid[], int m, int n, int start_x, int start_y,
	int goal_x, int goal_y, double *ex, double *ey) {

	Node *node;

	node_list = calloc(m * n, sizeof(Node));
	num_row = m;
	num_col = n;
	grid = _grid;
	start = node_list + start_y + start_x * n;
	goal = node_list + goal_y + goal_x * n;
	for (int x = 0; x < m; x++) {
		for (int y = 0; y < n; y++) {
			node = node_list + y + x * n;
			node->x = x;
			node->y = y;
			node->f = 0.0;
			node->g = 0.0;
			node->h = 0.0;
			node->open = false;
			node->closed = false;
		}
	}
	a_star();
	if (start->next == NULL) {
		*ex = 0.0;
		*ey = 0.0;
	}
	else {
		double dx = start->next->x - start->x;
		double dy = start->next->y - start->y;
		double norm = sqrt(dx * dx + dy * dy);
		*ex = dx / norm;
		*ey = dy / norm;
	}
}